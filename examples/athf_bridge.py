#!/usr/bin/env python3
"""
athf_bridge.py — Ingest completed ATHF hunt files into ZettelForge.

Parses LOCK-pattern markdown, extracts MITRE techniques and IOCs,
stores each hunt as a ZettelForge memory note with CTI metadata,
and wires entity relationships into the knowledge graph.

Usage:
    # Single hunt
    python athf_bridge.py /path/to/hunts/H-0042.md

    # All hunts in a directory (recursive)
    python athf_bridge.py /path/to/hunts/

    # Dry-run — parse and print, don't ingest
    python athf_bridge.py --dry-run /path/to/hunts/
"""

import re
import sys
import yaml
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from zettelforge import MemoryManager, get_memory_manager


# ---------------------------------------------------------------------------
# ATHF hunt parser (mirrors athf.core.hunt_parser logic)
# ---------------------------------------------------------------------------

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

_LOCK_PATTERNS = {
    "learn": re.compile(r"##\s+LEARN[:\s].*?(?=##\s+OBSERVE|$)", re.DOTALL | re.IGNORECASE),
    "observe": re.compile(r"##\s+OBSERVE[:\s].*?(?=##\s+CHECK|$)", re.DOTALL | re.IGNORECASE),
    "check": re.compile(r"##\s+CHECK[:\s].*?(?=##\s+KEEP|$)", re.DOTALL | re.IGNORECASE),
    "keep": re.compile(r"##\s+KEEP[:\s].*?(?=##\s+[A-Z]|$)", re.DOTALL | re.IGNORECASE),
}

# Regex for extracting IOCs from hunt body text
_IOC_PATTERNS = {
    "ipv4": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
    "domain": re.compile(r"\b[a-zA-Z0-9][-a-zA-Z0-9]*\.[a-zA-Z]{2,}\b"),
    "md5": re.compile(r"\b[a-fA-F0-9]{32}\b"),
    "sha256": re.compile(r"\b[a-fA-F0-9]{64}\b"),
    "cve": re.compile(r"\bCVE-\d{4}-\d{4,}\b", re.IGNORECASE),
}

# Common domains to exclude from IOC extraction
_DOMAIN_EXCLUDE = {
    "github.com", "example.com", "microsoft.com", "apple.com",
    "google.com", "splunk.com", "crowdstrike.com", "mitre.org",
}


def parse_hunt(path: Path) -> Optional[Dict]:
    """Parse an ATHF hunt markdown file into structured data."""
    text = path.read_text(encoding="utf-8")

    fm_match = _FRONTMATTER_RE.match(text)
    if not fm_match:
        return None

    try:
        frontmatter = yaml.safe_load(fm_match.group(1))
    except yaml.YAMLError:
        return None

    if not frontmatter or "hunt_id" not in frontmatter:
        return None

    body = text[fm_match.end():]
    sections = {}
    for name, pattern in _LOCK_PATTERNS.items():
        m = pattern.search(body)
        sections[name] = m.group(0).strip() if m else ""

    return {
        "path": str(path),
        "frontmatter": frontmatter,
        "body": body,
        "sections": sections,
    }


def extract_iocs(text: str) -> List[Dict]:
    """Pull IOCs from free text, excluding common benign domains."""
    iocs = []
    seen = set()
    for ioc_type, pattern in _IOC_PATTERNS.items():
        for match in pattern.finditer(text):
            value = match.group(0)
            if ioc_type == "domain" and value.lower() in _DOMAIN_EXCLUDE:
                continue
            if value not in seen:
                seen.add(value)
                iocs.append({"type": ioc_type, "value": value})
    return iocs


# ---------------------------------------------------------------------------
# ZettelForge ingestion
# ---------------------------------------------------------------------------

def ingest_hunt(mm: MemoryManager, hunt: Dict, *, verbose: bool = False) -> str:
    """Store one parsed hunt in ZettelForge and link entities."""
    fm = hunt["frontmatter"]
    hunt_id = fm["hunt_id"]
    title = fm.get("title", hunt_id)
    status = fm.get("status", "unknown")
    techniques = fm.get("techniques", [])
    tactics = fm.get("tactics", [])
    platforms = fm.get("platform", [])
    tags = fm.get("tags", [])
    date = str(fm.get("date", ""))

    # Build note content — full LOCK body prefixed with metadata header
    header = (
        f"# {hunt_id}: {title}\n\n"
        f"**Status:** {status} | **Date:** {date}\n"
        f"**Tactics:** {', '.join(tactics)} | "
        f"**Techniques:** {', '.join(techniques)}\n"
        f"**Platform:** {', '.join(platforms)} | "
        f"**Tags:** {', '.join(tags)}\n"
    )
    content = header + "\n" + hunt["body"]

    # Store as memory note
    note, _ = mm.remember(content, domain="cti")

    if verbose:
        print(f"  [+] Stored {hunt_id} as note {note.id}")

    # Extract IOCs from CHECK and KEEP sections
    check_keep = hunt["sections"].get("check", "") + hunt["sections"].get("keep", "")
    iocs = extract_iocs(check_keep)

    # Wire up knowledge graph edges
    kg = mm.knowledge_graph

    # Hunt node
    kg.add_node("note", hunt_id)

    # MITRE technique nodes + edges
    for tech_id in techniques:
        kg.add_node("attack-pattern", tech_id)
        kg.add_edge("note", hunt_id, "attack-pattern", tech_id, "MENTIONED_IN")

    # IOC nodes + edges
    for ioc in iocs:
        entity_type = "indicator" if ioc["type"] == "cve" else "indicator"
        kg.add_node(entity_type, ioc["value"])
        kg.add_edge("note", hunt_id, entity_type, ioc["value"], "INDICATES")

    if verbose and iocs:
        print(f"       {len(iocs)} IOCs linked, {len(techniques)} techniques")

    return note.id


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def find_hunts(root: Path) -> List[Path]:
    """Recursively find hunt markdown files, skipping docs."""
    skip = {"README.md", "FORMAT_GUIDELINES.md", "INDEX.md",
            "AGENTS.md", "WEEKLY_SUMMARY_TEMPLATE.md"}
    hunts = []
    for p in sorted(root.rglob("*.md")):
        if p.name in skip:
            continue
        if p.name.startswith("H-") or _FRONTMATTER_RE.match(
            p.read_text(encoding="utf-8", errors="ignore")[:500]
        ):
            hunts.append(p)
    return hunts


def main():
    parser = argparse.ArgumentParser(
        description="Ingest ATHF hunt files into ZettelForge memory."
    )
    parser.add_argument("path", type=Path, help="Hunt file or directory of hunts")
    parser.add_argument("--dry-run", action="store_true", help="Parse only, don't ingest")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    if args.path.is_file():
        paths = [args.path]
    elif args.path.is_dir():
        paths = find_hunts(args.path)
    else:
        print(f"Error: {args.path} not found", file=sys.stderr)
        sys.exit(1)

    if not paths:
        print("No hunt files found.")
        sys.exit(0)

    print(f"Found {len(paths)} hunt file(s)")

    parsed = []
    for p in paths:
        hunt = parse_hunt(p)
        if hunt:
            parsed.append(hunt)
        elif args.verbose:
            print(f"  [!] Skipped {p.name} (no valid frontmatter)")

    print(f"Parsed {len(parsed)} valid hunt(s)")

    if args.dry_run:
        for h in parsed:
            fm = h["frontmatter"]
            techs = fm.get("techniques", [])
            iocs = extract_iocs(h["sections"].get("check", "") + h["sections"].get("keep", ""))
            print(f"  {fm['hunt_id']}: {fm.get('title', '?')}")
            print(f"    techniques={techs}  iocs={len(iocs)}  status={fm.get('status')}")
        return

    mm = get_memory_manager()
    ingested = 0
    for hunt in parsed:
        try:
            ingest_hunt(mm, hunt, verbose=args.verbose)
            ingested += 1
        except Exception as e:
            print(f"  [!] Failed {hunt['frontmatter']['hunt_id']}: {e}", file=sys.stderr)

    print(f"\nIngested {ingested}/{len(parsed)} hunts into ZettelForge")
    print("Run `zettelforge recall 'your query'` to search across hunts.")


if __name__ == "__main__":
    main()
