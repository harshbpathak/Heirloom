"""Print the SHA-256 of this skill's SKILL.md (the capture workflow version)."""

import hashlib
from pathlib import Path

skill_md = Path(__file__).with_name("SKILL.md")
print(hashlib.sha256(skill_md.read_bytes()).hexdigest())
