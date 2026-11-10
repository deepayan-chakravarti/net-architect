"""CLI exit codes and the web API."""

import json
import threading
import urllib.error
import urllib.request

import pytest

from netarchitect.cli import main
from netarchitect.web.server import make_server


# ------------------------------------------------------------------------- CLI
def test_cli_plan_preset(capsys):
    assert main(["plan", "--preset", "campus_lan"]) == 0
    out = capsys.readouterr().out
    assert "ARCHITECTURAL RATIONALE LOG" in out and "Single-area OSPF" in out


def test_cli_plan_json(capsys):
    assert main(["plan", "--preset", "metro_man", "--format", "json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["meta"]["profile"] == "metro_man"


def test_cli_copper_violation_exit_code(capsys):
    assert main(["media", "--distance", "150", "--prefer", "copper"]) == 3
    err = capsys.readouterr().err
    assert "PHYSICAL_DISTANCE_VIOLATION" in err and "attenuation" in err


def test_cli_vlsm_exhaustion_exit_code(capsys):
    assert main(["vlsm", "192.168.1.0/24", "200", "100"]) == 4
    assert "ADDRESS_SPACE_EXHAUSTED" in capsys.readouterr().err


def test_cli_vlsm_ok(capsys):
    assert main(["vlsm", "192.168.1.0/24", "100", "50", "--p2p", "2"]) == 0
    assert "192.168.1.0/25" in capsys.readouterr().out


def test_cli_invalid_custom_input_exit_code(tmp_path, capsys):
    f = tmp_path / "bad.json"
    f.write_text(json.dumps({"name": "x", "network_type": "campus", "root_prefix": "10.0.0.0/16",
                             "sites": []}))
    assert main(["plan", "--input", str(f)]) == 2
    assert "VALIDATION_FAILED" in capsys.readouterr().err


def test_cli_malformed_json_file(tmp_path, capsys):
    f = tmp_path / "broken.json"
    f.write_text("{not json")
    assert main(["plan", "--input", str(f)]) == 1
    assert "invalid JSON" in capsys.readouterr().err


def test_cli_wildcard(capsys):
    assert main(["wildcard", "10.1.4.0/22"]) == 0
    assert "0.0.3.255" in capsys.readouterr().out


def test_cli_export_all(tmp_path, capsys):
    assert main(["export-all", "--out", str(tmp_path)]) == 0
    for pid in ("campus_lan", "metro_man", "global_wan"):
        assert (tmp_path / f"{pid}_configs.txt").exists()


# ------------------------------------------------------------------------- web
@pytest.fixture(scope="module")
def base_url():
    srv = make_server("127.0.0.1", 0, verbose=False)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{srv.server_port}"
    srv.shutdown()
    srv.server_close()


def call(url, body=None, raw=None):
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def test_web_index_and_presets(base_url):
    status, body = call(base_url + "/")
    assert status == 200 and b"NetArchitect" in body
    status, body = call(base_url + "/api/presets")
    assert status == 200 and len(json.loads(body)) == 3


def test_web_plan_preset(base_url):
    _, preset = call(base_url + "/api/presets/global_wan")
    status, body = call(base_url + "/api/plan", json.loads(preset))
    data = json.loads(body)
    assert status == 200 and data["routing"]["design"] == "Multi-area OSPF"


def test_web_media_violation_is_422_with_attenuation(base_url):
    status, body = call(base_url + "/api/media", {"distance_m": 150, "preference": "copper"})
    data = json.loads(body)
    assert status == 422 and data["error"] == "PhysicalDistanceViolationError"
    assert data["details"]["attenuation_warning"]


def test_web_validation_error_lists_issues(base_url):
    status, body = call(base_url + "/api/plan", {"name": "x"})
    data = json.loads(body)
    assert status == 422 and data["code"] == "VALIDATION_FAILED" and data["details"]["issues"]


def test_web_bad_json_and_unknown_route(base_url):
    assert call(base_url + "/api/plan", raw=b"{oops")[0] == 400
    assert call(base_url + "/api/nope")[0] == 404
    assert call(base_url + "/api/presets/../../etc")[0] == 404


def test_web_tools(base_url):
    status, body = call(base_url + "/api/vlsm", {"root": "10.0.0.0/24", "hosts": [100, 50]})
    assert status == 200 and json.loads(body)["subnets"][0]["cidr"] == "10.0.0.0/25"
    status, body = call(base_url + "/api/wildcard", {"cidr": "172.16.0.0/12"})
    assert json.loads(body)["wildcard"] == "0.15.255.255"
    assert call(base_url + "/api/vlsm", {"root": "10.0.0.0/30", "hosts": [500]})[0] == 422
