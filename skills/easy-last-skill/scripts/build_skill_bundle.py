#!/usr/bin/env python3
"""Erstellt ein einfaches .skill-Bundle fuer EasyLastSkill."""

from __future__ import annotations

import argparse
import zipfile
from pathlib import Path


def build_bundle(repo_root: Path, output: Path) -> Path:
    skill_root = repo_root / "skills" / "easy-last-skill"
    if not skill_root.exists():
        raise SystemExit(f"Skill-Ordner nicht gefunden: {skill_root}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in skill_root.rglob("*"):
            if path.is_file() and "__pycache__" not in path.parts:
                archive.write(path, path.relative_to(skill_root))
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="EasyLastSkill als .skill-Bundle packen.")
    parser.add_argument("--output", default="dist/EasyLastSkill.skill", help="Zielpfad")
    args = parser.parse_args()
    repo_root = Path(__file__).resolve().parents[3]
    output = build_bundle(repo_root, repo_root / args.output)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
