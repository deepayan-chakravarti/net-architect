"""Zero-dependency web dashboard + JSON API (stdlib http.server).

    GET  /                     dashboard (static/index.html)
    GET  /api/presets          list preset scenarios
    GET  /api/presets/<id>     preset parameter JSON
    POST /api/plan             full engine run         body: parameter JSON
    POST /api/vlsm             VLSM calculator         body: {root, hosts[], p2p, p2p_prefix}
    POST /api/media            L1 media selector       body: {distance_m, bandwidth_gbps, ...}
    POST /api/wildcard         mask/wildcard helper    body: {cidr}

Domain errors come back as HTTP 422 with the structured error
(e.g. PhysicalDistanceViolationError incl. its attenuation warning).
"""

from __future__ import annotations

import json
import mimetypes
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .. import ipmath as ip
from .. import media as media_engine
from ..engine import VERSION, plan
from ..errors import NetArchitectError
from ..presets import PRESET_IDS, list_presets, load_preset
from ..rationale import RationaleLog
from ..vlsm import SubnetRequest, allocate

STATIC = Path(__file__).parent / "static"
STATIC_FILES = {"/": "index.html", "/index.html": "index.html", "/app.js": "app.js",
                "/style.css": "style.css"}
MAX_BODY = 1_000_000


def api_vlsm(body: dict) -> dict:
    hosts = body.get("hosts") or []
    if not isinstance(hosts, list) or not hosts:
        raise ValueError("hosts must be a non-empty list of positive integers")
    names = body.get("names") or []
    reqs = [SubnetRequest(names[i] if i < len(names) and names[i] else f"LAN{i + 1}", h)
            for i, h in enumerate(hosts)]
    reqs += [SubnetRequest(f"P2P{i}", 2, "p2p") for i in range(1, int(body.get("p2p", 0)) + 1)]
    log = RationaleLog()
    alloc = allocate(body.get("root", ""), reqs, int(body.get("p2p_prefix", 30)), log)
    d = alloc.to_dict()
    d["subnets"].sort(key=lambda s: ip.ip_to_int(s["network"]))
    d["rationale"] = log.to_dicts()
    return d


def api_media(body: dict) -> dict:
    log = RationaleLog()
    dec = media_engine.select_media(
        float(body.get("distance_m", 0)), float(body.get("bandwidth_gbps", 10)),
        body.get("preference", "auto"), bool(body.get("poe", False)),
        body.get("transport", "fiber"), body.get("subject") or "cable run",
        float(body.get("margin_db", 1.0)), log)
    return {"decision": dec.to_dict(), "rationale": log.to_dicts()}


def api_wildcard(body: dict) -> dict:
    net, prefix = ip.parse_cidr(body.get("cidr", ""), strict=False)
    return {"network": ip.cidr_str(net, prefix), "mask": ip.mask_str(prefix),
            "wildcard": ip.wildcard_str(prefix),
            "broadcast": ip.int_to_ip(ip.broadcast_of(net, prefix)),
            "usable": ip.usable_hosts(prefix), "block_size": ip.block_size(prefix)}


class Handler(BaseHTTPRequestHandler):
    server_version = f"NetArchitect/{VERSION}"

    def log_message(self, fmt, *args):  # quieter console
        if getattr(self.server, "verbose", True):
            super().log_message(fmt, *args)

    def _send(self, status: int, payload, ctype="application/json") -> None:
        data = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):  # noqa: N802
        path = self.path.split("?")[0]
        if path in STATIC_FILES:
            f = STATIC / STATIC_FILES[path]
            ctype = mimetypes.guess_type(f.name)[0] or "text/plain"
            return self._send(200, f.read_bytes(), f"{ctype}; charset=utf-8")
        if path == "/api/presets":
            return self._send(200, list_presets())
        if path.startswith("/api/presets/"):
            pid = path.rsplit("/", 1)[-1]
            if pid in PRESET_IDS:
                return self._send(200, load_preset(pid))
        if path == "/api/health":
            return self._send(200, {"status": "ok", "version": VERSION})
        return self._send(404, {"error": "NotFound", "message": f"no route for {path}"})

    def do_POST(self):  # noqa: N802
        path = self.path.split("?")[0]
        routes = {"/api/plan": plan, "/api/vlsm": api_vlsm, "/api/media": api_media,
                  "/api/wildcard": api_wildcard}
        if path not in routes:
            return self._send(404, {"error": "NotFound", "message": f"no route for {path}"})
        try:
            length = int(self.headers.get("Content-Length", 0))
        except ValueError:
            length = -1
        if length < 0 or length > MAX_BODY:
            return self._send(413, {"error": "PayloadTooLarge",
                                    "message": f"body must be <= {MAX_BODY} bytes"})
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError as exc:
            return self._send(400, {"error": "InvalidJSON", "code": "INVALID_JSON",
                                    "message": f"Request body is not valid JSON: {exc}"})
        try:
            return self._send(200, routes[path](body))
        except NetArchitectError as exc:
            return self._send(HTTPStatus.UNPROCESSABLE_ENTITY, exc.to_dict())
        except (ValueError, TypeError, KeyError, AttributeError) as exc:
            return self._send(400, {"error": type(exc).__name__, "code": "BAD_REQUEST",
                                    "message": str(exc)})


def make_server(host: str = "127.0.0.1", port: int = 8080, verbose: bool = True):
    srv = ThreadingHTTPServer((host, port), Handler)
    srv.verbose = verbose
    return srv


def serve(host: str = "127.0.0.1", port: int = 8080) -> None:
    srv = make_server(host, port)
    print(f"NetArchitect dashboard running on http://{host}:{srv.server_port}  (Ctrl+C to stop)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()
