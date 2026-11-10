"""Preset scenario loader (presets are plain JSON so they double as custom-input examples)."""

from __future__ import annotations

import json
from pathlib import Path

PRESET_DIR = Path(__file__).parent
PRESET_IDS = ("campus_lan", "metro_man", "global_wan")


def list_presets() -> list[dict]:
    out = []
    for pid in PRESET_IDS:
        data = load_preset(pid)
        out.append({"id": pid, "name": data["name"], "description": data.get("description", ""),
                    "network_type": data["network_type"]})
    return out


def load_preset(preset_id: str) -> dict:
    if preset_id not in PRESET_IDS:
        raise KeyError(f"unknown preset '{preset_id}'; choose one of {', '.join(PRESET_IDS)}")
    return json.loads((PRESET_DIR / f"{preset_id}.json").read_text(encoding="utf-8"))
