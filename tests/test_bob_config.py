"""Validate the Bob integration files (spec §7): custom mode, skills, MCP config."""

import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
BOB = ROOT / ".bob"


def _front_matter(path: Path) -> dict:
    match = re.match(r"^---\n(.*?)\n---\n", path.read_text(encoding="utf-8"), re.DOTALL)
    assert match, f"{path} has no YAML front matter"
    return yaml.safe_load(match.group(1))


def test_archivist_mode_is_valid():
    data = yaml.safe_load((BOB / "custom_modes.yaml").read_text(encoding="utf-8"))
    modes = {m["slug"]: m for m in data["customModes"]}
    archivist = modes["archivist"]
    assert "Archivist" in archivist["name"]
    # Bob names the spec's "command" group "execute".
    assert set(archivist["groups"]) == {"read", "edit", "execute", "mcp"}
    for tool in ("ask_why", "impact_if_changed", "record_decision"):
        assert tool in archivist["roleDefinition"]


def test_skills_have_required_front_matter():
    for name in ("capture-why", "onboard-me"):
        front = _front_matter(BOB / "skills" / name / "SKILL.md")
        assert front["name"] == name  # must match the folder name
        assert front["description"]


def test_capture_why_hash_script_matches_sha256():
    import hashlib

    out = subprocess.run(
        [sys.executable, str(BOB / "skills" / "capture-why" / "skill_hash.py")],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    expected = hashlib.sha256(
        (BOB / "skills" / "capture-why" / "SKILL.md").read_bytes()
    ).hexdigest()
    assert out == expected


def test_mcp_json_registers_heirloom():
    data = json.loads((BOB / "mcp.json").read_text(encoding="utf-8"))
    server = data["mcpServers"]["heirloom"]
    assert server["args"] == ["mcp"]
