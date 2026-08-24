#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["PyYAML>=6.0"]
# ///
"""Validate SKILL.md files against the Agent Skills specification.

Spec: https://agentskills.io/specification

Each skill lives at skills/<name>/SKILL.md and must carry YAML frontmatter with,
at minimum, `name` and `description`. `name` must match its directory name and be
kebab-case. Optional spec fields (license, compatibility, metadata, allowed-tools)
are type-checked when present.

Exit code 0 = all valid, 1 = one or more violations.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

SKILLS_DIR = Path("skills")
KEBAB = "abcdefghijklmnopqrstuvwxyz0123456789-"

# Fields the Agent Skills spec defines. `name`/`description` required; rest optional.
REQUIRED_FIELDS = ("name", "description")
OPTIONAL_STRING_FIELDS = ("license",)
OPTIONAL_LIST_FIELDS = ("allowed-tools", "disallowed-tools", "compatibility")
DESCRIPTION_MAX = 1024


def is_kebab(value: str) -> bool:
    return bool(value) and all(c in KEBAB for c in value) and not value.startswith("-") and not value.endswith("-")


def parse_frontmatter(text: str, errors: list[str], rel: str) -> dict | None:
    if not text.startswith("---"):
        errors.append(f"{rel}: missing YAML frontmatter (file must start with '---')")
        return None
    parts = text.split("---", 2)
    if len(parts) < 3:
        errors.append(f"{rel}: malformed frontmatter (no closing '---')")
        return None
    try:
        data = yaml.safe_load(parts[1])
    except yaml.YAMLError as exc:
        errors.append(f"{rel}: invalid YAML in frontmatter: {exc}")
        return None
    if not isinstance(data, dict):
        errors.append(f"{rel}: frontmatter must be a YAML mapping")
        return None
    return data


def validate_skill(skill_md: Path, errors: list[str]) -> None:
    rel = str(skill_md)
    data = parse_frontmatter(skill_md.read_text(encoding="utf-8"), errors, rel)
    if data is None:
        return

    for field in REQUIRED_FIELDS:
        if field not in data or not str(data.get(field, "")).strip():
            errors.append(f"{rel}: required field '{field}' is missing or empty")

    dir_name = skill_md.parent.name
    name = data.get("name")
    if isinstance(name, str):
        if not is_kebab(name):
            errors.append(f"{rel}: 'name' must be kebab-case (got {name!r})")
        if name != dir_name:
            errors.append(f"{rel}: 'name' ({name!r}) must match directory name ({dir_name!r})")
    elif name is not None:
        errors.append(f"{rel}: 'name' must be a string")

    desc = data.get("description")
    if isinstance(desc, str):
        if len(desc) > DESCRIPTION_MAX:
            errors.append(f"{rel}: 'description' exceeds {DESCRIPTION_MAX} chars ({len(desc)})")
    elif desc is not None:
        errors.append(f"{rel}: 'description' must be a string")

    for field in OPTIONAL_STRING_FIELDS:
        if field in data and not isinstance(data[field], str):
            errors.append(f"{rel}: optional field '{field}' must be a string")

    for field in OPTIONAL_LIST_FIELDS:
        if field in data and not isinstance(data[field], list):
            errors.append(f"{rel}: optional field '{field}' must be a list")


def main() -> int:
    if not SKILLS_DIR.is_dir():
        print(f"No {SKILLS_DIR}/ directory found; nothing to validate.")
        return 0

    skill_files = sorted(SKILLS_DIR.glob("*/SKILL.md"))
    errors: list[str] = []

    # Every immediate subdirectory of skills/ must be a valid skill.
    for child in sorted(SKILLS_DIR.iterdir()):
        if child.is_dir() and not (child / "SKILL.md").is_file():
            errors.append(f"{child}/: skill directory has no SKILL.md")

    for skill_md in skill_files:
        validate_skill(skill_md, errors)

    if errors:
        print(f"SKILL.md validation failed ({len(errors)} issue(s)):", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    print(f"Validated {len(skill_files)} skill(s): all conform to the Agent Skills spec.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
