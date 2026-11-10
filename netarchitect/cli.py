"""Command-line interface.

    python -m netarchitect presets
    python -m netarchitect plan --preset metro_man [--format text|json|markdown] [--export DIR]
    python -m netarchitect plan --input my_network.json
    python -m netarchitect export-all --out exports
    python -m netarchitect vlsm 10.0.0.0/22 200 100 50 --p2p 2
    python -m netarchitect media --distance 250 [--bandwidth 10] [--prefer copper] [--poe]
    python -m netarchitect wildcard 10.1.4.0/22
    python -m netarchitect serve [--port 8080]

Exit codes: 0 ok, 1 generic, 2 validation/address error, 3 physical distance
violation, 4 address-space exhaustion.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import ipmath as ip
from . import media as media_engine
from .engine import VERSION, plan
from .errors import NetArchitectError
from .presets import PRESET_IDS, list_presets, load_preset
from .rationale import RationaleLog
from .vlsm import SubnetRequest, allocate


def _out(text: str) -> None:
    sys.stdout.write(text + ("\n" if not text.endswith("\n") else ""))


def _table(rows: list[list[str]], headers: list[str]) -> str:
    widths = [max(len(str(x)) for x in col) for col in zip(headers, *rows)]
    fmt = "  ".join(f"{{:<{w}}}" for w in widths)
    lines = [fmt.format(*headers), fmt.format(*["-" * w for w in widths])]
    lines += [fmt.format(*map(str, r)) for r in rows]
    return "\n".join(lines)


def render_text(result: dict, show_configs: bool = False) -> str:
    m = result["meta"]
    out = [f"NetArchitect v{result['version']} - {m['name']} ({m['network_type']}, "
           f"resiliency {m['resiliency']})",
           f"Topology tier : {result['topology']['tier']}",
           f"Routing       : {result['routing']['design']}"
           + (f" + eBGP AS{result['routing']['bgp']['asn']}" if result["routing"]["bgp"] else ""),
           f"Verification  : {result['verification']['passed']}/"
           f"{result['verification']['total']} packet-flow checks passed", ""]
    out.append("PHYSICAL MEDIA")
    rows = [[l["subject"], l["medium"], l["transceiver"], f"{l['distance_m'] / 1000:g} km",
             f"{l['budget']['headroom_db']} dB" if l["budget"] else "-",
             f"{l['latency_ms']:.3f}"] for l in result["media"]["links"]]
    rows += [[r["subject"], r["medium"], r["transceiver"], f"{r['distance_m']:g} m",
              f"{r['budget']['headroom_db']} dB" if r["budget"] else "-",
              f"{r['latency_ms']:.4f}"] for r in result["media"]["cable_runs"]]
    out.append(_table(rows, ["Link", "Medium", "Transceiver", "Distance", "Headroom", "ms"]))
    out += ["", f"ADDRESSING  root {result['addressing']['root']}  "
                f"({result['addressing']['root_utilization_pct']}% used, "
                f"{result['addressing']['address_efficiency_pct']}% host efficiency)"]
    rows = []
    for b in result["addressing"]["blocks"]:
        for s in b["subnets"]:
            rows.append([b["site"], s["name"], s["vlan_id"] or "-", s["cidr"], s["gateway"] or "-",
                         s["broadcast"], s["wildcard"], f"{s['utilization_pct']}%"])
    out.append(_table(rows, ["Site", "Subnet", "VLAN", "CIDR", "Gateway", "Broadcast",
                             "Wildcard", "Util"]))
    out += ["", "ARCHITECTURAL RATIONALE LOG", result["rationale_text"]]
    if show_configs:
        for name, cfg in result["configs"].items():
            out += ["", f"#### {name} ####", cfg]
    return "\n".join(out)


def render_markdown(result: dict) -> str:
    m = result["meta"]
    lines = [f"# {m['name']} - NetArchitect plan", "",
             f"* **Topology tier:** {result['topology']['tier']}",
             f"* **Routing:** {result['routing']['design']}",
             f"* **Root prefix:** {m['root_prefix']}",
             f"* **Verification:** {result['verification']['passed']}/"
             f"{result['verification']['total']} checks passed", "",
             "## Architectural rationale", ""]
    for i, e in enumerate(result["rationale"], 1):
        lines.append(f"{i}. **[{e['domain']}] {e['subject']} - {e['decision']}**  ")
        lines.append(f"   {e['justification']}" +
                     (f"  _({', '.join(e['references'])})_" if e["references"] else ""))
    lines += ["", "## Device configurations", ""]
    for name, cfg in result["configs"].items():
        lines += [f"### {name}", "", "```cisco", cfg.rstrip(), "```", ""]
    return "\n".join(lines)


def export_plan(result: dict, out_dir: Path, stem: str) -> list[Path]:
    """Write the combined config file, per-device .cfg files, rationale and JSON."""
    out_dir.mkdir(parents=True, exist_ok=True)
    dev_dir = out_dir / stem
    dev_dir.mkdir(exist_ok=True)
    written = []
    cab = ["! CABLING PLAN (connect these ports in Packet Tracer / GNS3 before pasting)"]
    for c in result["cabling"]:
        cab.append(f"!   {c['a']:<20} {c['a_port']:<24} <-> {c['b']:<20} {c['b_port']:<24} "
                   f"{c['medium']}")
    combined = [f"! NetArchitect v{result['version']} export - {result['meta']['name']}",
                f"! Topology: {result['topology']['tier']} | Routing: "
                f"{result['routing']['design']}", "!"] + cab + ["!"]
    for name, cfg in result["configs"].items():
        p = dev_dir / f"{name}.cfg"
        p.write_text(cfg, encoding="utf-8")
        written.append(p)
        combined += ["", "!" * 72, f"! DEVICE: {name}", "!" * 72, cfg]
    combo = out_dir / f"{stem}_configs.txt"
    combo.write_text("\n".join(combined), encoding="utf-8")
    rat = out_dir / f"{stem}_rationale.md"
    rat.write_text(render_markdown(result), encoding="utf-8")
    js = out_dir / f"{stem}_plan.json"
    js.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return [combo, rat, js] + written


def _load_input(args) -> tuple[dict, str]:
    if args.preset:
        return load_preset(args.preset), args.preset
    path = Path(args.input)
    try:
        return json.loads(path.read_text(encoding="utf-8")), path.stem
    except json.JSONDecodeError as exc:
        raise NetArchitectError(f"{path}: invalid JSON ({exc})") from exc
    except OSError as exc:
        raise NetArchitectError(f"cannot read {path}: {exc.strerror}") from exc


def cmd_plan(args) -> int:
    raw, stem = _load_input(args)
    result = plan(raw)
    if args.format == "json":
        _out(json.dumps(result, indent=2))
    elif args.format == "markdown":
        _out(render_markdown(result))
    else:
        _out(render_text(result, show_configs=args.configs))
    if args.export:
        files = export_plan(result, Path(args.export), stem)
        sys.stderr.write(f"exported {len(files)} files to {args.export}\n")
    return 0


def cmd_export_all(args) -> int:
    out = Path(args.out)
    for pid in PRESET_IDS:
        files = export_plan(plan(load_preset(pid)), out, pid)
        _out(f"{pid}: {files[0]} (+{len(files) - 1} files)")
    return 0


def cmd_presets(_args) -> int:
    _out(_table([[p["id"], p["network_type"], p["name"], p["description"][:70]]
                 for p in list_presets()], ["id", "type", "name", "description"]))
    return 0


def cmd_vlsm(args) -> int:
    reqs = [SubnetRequest(f"LAN{i}", h) for i, h in enumerate(args.hosts, 1)]
    reqs += [SubnetRequest(f"P2P{i}", 2, "p2p") for i in range(1, args.p2p + 1)]
    log = RationaleLog()
    alloc = allocate(args.root, reqs, args.p2p_prefix, log)
    rows = [[s.name, s.hosts_requested, s.cidr, ip.int_to_ip(s.mask), ip.int_to_ip(s.wildcard),
             ip.int_to_ip(s.gateway) if s.gateway is not None else "-",
             ip.int_to_ip(s.broadcast), s.usable, f"{s.utilization * 100:.1f}%"]
            for s in sorted(alloc.subnets, key=lambda s: s.network)]
    _out(_table(rows, ["Name", "Hosts", "CIDR", "Mask", "Wildcard", "Gateway", "Broadcast",
                       "Usable", "Util"]))
    d = alloc.to_dict()
    _out(f"\n{d['allocated']:,} of {d['root_size']:,} addresses used "
         f"({d['root_utilization_pct']}%), {d['free']:,} free.\n")
    _out(log.to_text())
    return 0


def cmd_media(args) -> int:
    log = RationaleLog()
    dec = media_engine.select_media(args.distance, args.bandwidth, args.prefer, args.poe,
                                    args.transport, "cable run", args.margin, log)
    _out(f"{dec.medium} / {dec.transceiver} ({dec.standard})")
    _out(log.to_text())
    return 0


def cmd_wildcard(args) -> int:
    net, prefix = ip.parse_cidr(args.cidr, strict=False)
    _out(_table([[ip.cidr_str(net, prefix), ip.mask_str(prefix), ip.wildcard_str(prefix),
                  ip.int_to_ip(ip.broadcast_of(net, prefix)), ip.usable_hosts(prefix)]],
                ["Network", "Mask", "Wildcard", "Broadcast", "Usable"]))
    _out(f"\nWildcard = ~mask & 0xFFFFFFFF = {ip.wildcard(prefix):#010x}")
    return 0


def cmd_serve(args) -> int:
    from .web.server import serve
    serve(args.host, args.port)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="netarchitect",
                                description="NetArchitect: Recommendation & Config Engine")
    p.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("plan", help="run the full engine on a preset or custom JSON")
    src = sp.add_mutually_exclusive_group(required=True)
    src.add_argument("--preset", choices=PRESET_IDS)
    src.add_argument("--input", help="path to a custom parameter JSON file")
    sp.add_argument("--format", choices=("text", "json", "markdown"), default="text")
    sp.add_argument("--configs", action="store_true", help="include configs in text output")
    sp.add_argument("--export", metavar="DIR", help="write configs + rationale to DIR")
    sp.set_defaults(func=cmd_plan)

    sp = sub.add_parser("export-all", help="export all three preset profiles")
    sp.add_argument("--out", default="exports")
    sp.set_defaults(func=cmd_export_all)

    sp = sub.add_parser("presets", help="list preset scenarios")
    sp.set_defaults(func=cmd_presets)

    sp = sub.add_parser("vlsm", help="stand-alone VLSM calculator")
    sp.add_argument("root", help="root prefix, e.g. 10.0.0.0/16")
    sp.add_argument("hosts", nargs="+", type=int, help="host counts per LAN")
    sp.add_argument("--p2p", type=int, default=0, help="number of point-to-point links")
    sp.add_argument("--p2p-prefix", type=int, choices=(30, 31), default=30)
    sp.set_defaults(func=cmd_vlsm)

    sp = sub.add_parser("media", help="stand-alone L1 media selector")
    sp.add_argument("--distance", type=float, required=True, help="metres")
    sp.add_argument("--bandwidth", type=float, default=10, help="Gbps")
    sp.add_argument("--prefer", choices=("auto", "copper", "fiber"), default="auto")
    sp.add_argument("--transport", choices=("fiber", "evpl", "internet"), default="fiber")
    sp.add_argument("--poe", action="store_true")
    sp.add_argument("--margin", type=float, default=1.0, help="optical safety margin dB")
    sp.set_defaults(func=cmd_media)

    sp = sub.add_parser("wildcard", help="mask / wildcard / broadcast for a prefix")
    sp.add_argument("cidr")
    sp.set_defaults(func=cmd_wildcard)

    sp = sub.add_parser("serve", help="start the web dashboard")
    sp.add_argument("--host", default="127.0.0.1")
    sp.add_argument("--port", type=int, default=8080)
    sp.set_defaults(func=cmd_serve)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except NetArchitectError as exc:
        sys.stderr.write(f"error [{exc.code}]: {exc.message}\n")
        att = exc.details.get("attenuation_warning")
        if att:
            sys.stderr.write(f"  signal attenuation warning: {att}\n")
        for issue in exc.details.get("issues", []):
            sys.stderr.write(f"  - {issue}\n")
        return exc.exit_code
    except (ValueError, KeyError) as exc:
        sys.stderr.write(f"error: {exc}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
