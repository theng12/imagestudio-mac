#!/usr/bin/env python3
"""Require shipped changes to carry a version bump and visible release notes.

Use ``python3 release_metadata_check.py <base-ref>`` before publishing a
change. The GitHub workflow runs the same command for pull requests and pushes.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
METADATA_FILES = {"VERSION", "CHANGELOG.md"}
SEMVER_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
RELEASE_HEADING_RE = re.compile(r"(?m)^## \[(?P<version>[^\]]+)\].*$")


def parse_version(value: str, source: str) -> tuple[int, int, int]:
    match = SEMVER_RE.fullmatch(value.strip())
    if not match:
        raise ValueError(f"{source} must contain an X.Y.Z semantic version.")
    return tuple(int(part) for part in match.groups())


def release_section(changelog: str, version: str) -> str | None:
    headings = list(RELEASE_HEADING_RE.finditer(changelog))
    if not headings or headings[0].group("version") != version:
        return None
    end = headings[1].start() if len(headings) > 1 else len(changelog)
    return changelog[headings[0].end():end]


def has_visible_detail(section: str) -> bool:
    return any(line.startswith("- ") and len(line) > 2 for line in section.splitlines())


def validate(
    *,
    changed_paths: set[str],
    base_version: str,
    current_version: str,
    changelog: str,
) -> list[str]:
    """Return publication errors for a diff; an empty list is valid."""
    if not (changed_paths - METADATA_FILES):
        return []

    errors: list[str] = []
    if not METADATA_FILES <= changed_paths:
        errors.append("Non-metadata changes require both VERSION and CHANGELOG.md updates.")

    try:
        if parse_version(current_version, "VERSION") <= parse_version(base_version, "base VERSION"):
            errors.append("VERSION must increase for non-metadata changes.")
    except ValueError as exc:
        errors.append(str(exc))

    section = release_section(changelog, current_version.strip())
    if section is None:
        errors.append("The first CHANGELOG release heading must match the current VERSION.")
    elif not has_visible_detail(section):
        errors.append("The current CHANGELOG release needs at least one visible '- ' detail for What's New.")
    return errors


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def changed_paths_since(base_ref: str) -> set[str]:
    """Include committed, staged, unstaged, and newly created files.

    CI only has the first category. Developers run this before committing, so
    the other three categories must be part of the same release decision.
    """
    commands = (
        ("diff", "--name-only", f"{base_ref}...HEAD"),
        ("diff", "--name-only"),
        ("diff", "--name-only", "--cached"),
        ("ls-files", "--others", "--exclude-standard"),
    )
    return {
        path
        for command in commands
        for path in git(*command).splitlines()
        if path
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base_ref", help="Git ref to compare against, such as origin/main")
    args = parser.parse_args()

    try:
        changed_paths = changed_paths_since(args.base_ref)
        base_version = git("show", f"{args.base_ref}:VERSION")
        current_version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"release metadata check could not read the comparison: {exc}", file=sys.stderr)
        return 2

    errors = validate(
        changed_paths=changed_paths,
        base_version=base_version,
        current_version=current_version,
        changelog=changelog,
    )
    if errors:
        print("Release metadata check failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("Release metadata check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
