#!/usr/bin/env python3
"""
Generate release notes from Conventional Commits since last tag.
"""

import re
import subprocess
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).parent


def get_commits_since_tag(tag: str) -> list:
    """Get commits since a tag."""
    try:
        result = subprocess.run(
            ["git", "log", f"{tag}..HEAD", "--pretty=format:%s"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip().split("\n") if result.stdout.strip() else []
    except subprocess.CalledProcessError:
        return []


def categorize_commit(message: str) -> tuple:
    """Categorize a conventional commit."""
    if not message:
        return None, None

    # Check for breaking change
    is_breaking = "!" in message or "BREAKING CHANGE:" in message

    # Parse type and scope
    match = re.match(r"^(\w+)(?:\(([^)]+)\))?:\s*(.+)$", message)
    if match:
        commit_type, scope, description = match.groups()
        return (commit_type, scope), description
    return None, message


def generate_release_notes() -> str:
    """Generate release notes from commits."""
    try:
        # Get current version
        version_file = PROJECT_DIR / "VERSION"
        current_version = version_file.read_text().strip()
    except FileNotFoundError:
        current_version = "1.0.0"

    # Get last tag
    result = subprocess.run(
        ["git", "describe", "--tags", "--abbrev=0"],
        capture_output=True,
        text=True,
    )
    last_tag = result.stdout.strip() if result.stdout.strip() else None

    if not last_tag:
        return f"# Release {current_version}\n\nNo previous tags found."

    commits = get_commits_since_tag(last_tag)
    if not commits:
        return f"# Release {current_version}\n\nNo changes since {last_tag}."

    # Categorize commits
    added = []
    changed = []
    fixed = []
    removed = []
    deprecated = []
    security = []
    other = []

    for commit in commits:
        (commit_type, scope), description = categorize_commit(commit)
        if commit_type == "feat":
            added.append(commit)
        elif commit_type == "fix":
            fixed.append(commit)
        elif commit_type == "perf":
            changed.append(commit)
        elif commit_type == "refactor":
            changed.append(commit)
        elif commit_type == "docs":
            other.append(commit)
        elif commit_type == "test":
            other.append(commit)
        elif commit_type == "chore":
            other.append(commit)
        elif commit_type == "security":
            security.append(commit)
        elif commit_type == "removed":
            removed.append(commit)
        elif commit_type == "deprecated":
            deprecated.append(commit)
        else:
            other.append(commit)

    # Build notes
    notes = [f"# Release {current_version}"]
    notes.append("")

    if added:
        notes.append("## Added")
        for commit in added:
            notes.append(f"- {commit}")
        notes.append("")

    if changed:
        notes.append("## Changed")
        for commit in changed:
            notes.append(f"- {commit}")
        notes.append("")

    if fixed:
        notes.append("## Fixed")
        for commit in fixed:
            notes.append(f"- {commit}")
        notes.append("")

    if security:
        notes.append("## Security")
        for commit in security:
            notes.append(f"- {commit}")
        notes.append("")

    if other:
        notes.append("## Miscellaneous")
        for commit in other:
            notes.append(f"- {commit}")
        notes.append("")

    notes.append(f"**Full Changelog:** https://github.com/.../compare/{last_tag}...v{current_version}")

    return "\n".join(notes)


if __name__ == "__main__":
    print(generate_release_notes())
