#!/usr/bin/env python3
"""
Version Management Script for A-MEM

This script handles version management operations including:
- Reading/writing version from VERSION file
- Generating version tags from Conventional Commits
- Creating release branches and tags
"""

import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

# Constants
SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
VERSION_FILE = PROJECT_DIR / "VERSION"
TAG_PREFIX = "v"
CHANGELOG_FILE = PROJECT_DIR / "CHANGELOG.md"


def read_version() -> str:
    """Read current version from VERSION file."""
    if not VERSION_FILE.exists():
        raise FileNotFoundError(f"VERSION file not found at {VERSION_FILE}")
    return VERSION_FILE.read_text().strip()


def write_version(version: str) -> None:
    """Write version to VERSION file."""
    VERSION_FILE.write_text(version + "\n")


def parse_semver(version: str) -> tuple:
    """Parse semantic version into (major, minor, patch)."""
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)(?:-(.+))?$", version)
    if not match:
        raise ValueError(f"Invalid semver: {version}")
    major, minor, patch, prerelease = match.groups()
    return int(major), int(minor), int(patch), prerelease or ""


def bump_version(version: str, bump_type: str) -> str:
    """Bump version based on type (major, minor, patch, prerelease)."""
    major, minor, patch, prerelease = parse_semver(version)

    if bump_type == "major":
        return f"{major + 1}.0.0"
    elif bump_type == "minor":
        return f"{major}.{minor + 1}.0"
    elif bump_type == "patch":
        return f"{major}.{minor}.{patch + 1}"
    elif bump_type == "prerelease":
        if prerelease:
            # Extract and increment prerelease number
            pre_match = re.match(r"^(.+?)(\d+)$", prerelease)
            if pre_match:
                pre_base, pre_num = pre_match.groups()
                return f"{major}.{minor}.{patch}-{pre_base}{int(pre_num) + 1}"
            return f"{major}.{minor}.{patch}-{prerelease}.1"
        return f"{major}.{minor}.{patch}-alpha.1"
    else:
        raise ValueError(f"Unknown bump type: {bump_type}")


def get_conventional_commits_since_tag(tag: str) -> list:
    """Get commits since a tag, categorized by conventional commit type."""
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


def calculate_version_bump(commits: list) -> str:
    """Calculate version bump based on conventional commits."""
    has_breaking = any("!" in c or "BREAKING CHANGE:" in c for c in commits)
    has_feat = any(c.startswith("feat") for c in commits)
    has_fix = any(c.startswith("fix") or c.startswith("perf") for c in commits)

    if has_breaking:
        return "major"
    elif has_feat:
        return "minor"
    elif has_fix:
        return "patch"
    return "none"


def update_changelog(version: str) -> None:
    """Update CHANGELOG.md with new release entry."""
    if not CHANGELOG_FILE.exists():
        # Create initial changelog
        CHANGELOG_FILE.write_text(
            f"""# Changelog

All notable changes to A-MEM are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [{version}] - {date.today().isoformat()}

### Added
- Initial A-MEM release with full implementation

## [Unreleased]

See git history for changes.
"""
        )
        return

    content = CHANGELOG_FILE.read_text()

    # Check if version already exists
    if f"[{version}]" in content:
        return

    # Find the [Unreleased] section and add new version
    header, rest = content.split("\n\n## [Unreleased]\n", 1)
    new_entry = f"\n## [{version}] - {date.today().isoformat()}\n\n### Added\n- Version {version} release\n\n## [Unreleased]\n{rest}"

    CHANGELOG_FILE.write_text(header + new_entry)


def create_release_branch(version: str) -> None:
    """Create release branch from main."""
    branch_name = f"release/v{version}"
    print(f"Creating release branch: {branch_name}")
    subprocess.run(["git", "checkout", "-b", branch_name], check=True)


def tag_release(version: str) -> None:
    """Create git tag for release."""
    tag = f"{TAG_PREFIX}{version}"
    print(f"Creating tag: {tag}")
    subprocess.run(["git", "tag", "-a", tag, "-m", f"Release {version}"], check=True)


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: version.py <command> [args]")
        print("Commands:")
        print("  current     Show current version")
        print("  bump <type> Bump version (major, minor, patch, prerelease)")
        print("  status      Show version status")
        print("  release     Create release (branch + tag + changelog)")
        sys.exit(1)

    command = sys.argv[1]

    if command == "current":
        print(read_version())

    elif command == "bump":
        if len(sys.argv) < 3:
            print("Error: bump type required (major, minor, patch, prerelease)")
            sys.exit(1)
        bump_type = sys.argv[2]
        if bump_type not in ["major", "minor", "patch", "prerelease"]:
            print(f"Error: invalid bump type: {bump_type}")
            sys.exit(1)

        current = read_version()
        new_version = bump_version(current, bump_type)
        write_version(new_version)
        print(f"Version bumped: {current} -> {new_version}")

    elif command == "status":
        current = read_version()
        print(f"Current version: {current}")

        # Check if on main branch
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
        )
        current_branch = result.stdout.strip()
        print(f"Current branch: {current_branch}")

        # Check for uncommitted changes
        result = subprocess.run(
            ["git", "status", "--porcelain"], capture_output=True, text=True
        )
        if result.stdout.strip():
            print("Uncommitted changes: YES")
        else:
            print("Uncommitted changes: NO")

    elif command == "release":
        current = read_version()
        print(f"Creating release for version {current}...")

        # Update changelog
        update_changelog(current)
        print("Updated CHANGELOG.md")

        # Create tag
        tag_release(current)
        print(f"Tagged release: {TAG_PREFIX}{current}")

        # Instructions for pushing
        print("\nTo publish this release:")
        print(f"  git push origin main")
        print(f"  git push origin {TAG_PREFIX}{current}")

    else:
        print(f"Error: unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
