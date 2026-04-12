#!/usr/bin/env python3
"""
athf_bridge.py — Ingest completed ATHF hunt files into ZettelForge.

Parses LOCK-pattern markdown hunts from the Agentic Threat Hunting
Framework, extracts MITRE techniques and IOCs, and stores them as
ZettelForge memory notes with knowledge graph edges.

Usage:
    python athf_bridge.py /path/to/hunts/           # ingest all hunts
    python athf_bridge.py /path/to/hunts/H-0042.md  # single hunt
    python athf_bridge.py --dry-run /path/to/hunts/  # parse only
"""

import re
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Optional

import yaml
from zettelforge import MemoryManager, get_memory_manager
from zettelforge.knowledge_graph import get_knowledge_graph

_FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_IOC_RE = {
    "cve": re.compile(r"\bCVE-\d{4}-\d{4,}\b", re.I),
    "ipv4": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
    "sha256": re.compile(r"\b[a-fA-F0-9]{64}\b"),
    "md5": re.compile(r"\b[a-fA-F0-9]{32}\b"),
}


def parse_hunt(path: Path) -> Optional[Dict]:
    """Parse an ATHF hunt markdown file into structured data."""
    text = path.read_text(encoding="utf-8", errors="ignore")
    m = _FM_RE.match(text)
    if not m:
        return None
    try:
        fm = yaml.safe_load(m.group(1))
    except yaml.YAMLError:
        return None
    if not fm or "hunt_id" not in fm:
        return None
    return {"path": str(path), "fm": fm, "body": text[m.end():]}


def extract_iocs(text: str) -> List[Dict]:
    """Pull IOCs from free text."""
    seen, out = set(), []
    for ioc_type, pat in _IOC_RE.items():
        for hit in pat.finditer(text):
            v = hit.group(0)
            if v not in seen:
                seen.add(v)
                out.append({"type": ioc_type, "value": v})
    return out


def ingest(mm: MemoryManager, hunt: Dict, verbose: bool = False) -> str:
    """Store one hunt in ZettelForge and link entities in the graph."""
    fm = hunt["fm"]
    hid = fm["hunt_id"]
    techs = fm.get("techniques", [])
    header = (
        f"# {hid}: {fm.get('title', hid)}\n"
        f"Status: {fm.get('status', '?')} | Tactics: {', '.join(fm.get('tactics', []))}\n"
        f"Techniques: {', '.join(techs)}\n"
    )
    note, _ = mm.remember(header + hunt["body"], domain="cti")

    kg = get_knowledge_graph()
    for t in techs:
        kg.add_edge("note", note.id, "attack-pattern", t, "MENTIONED_IN")
    for ioc in extract_iocs(hunt["body"]):
        kg.add_edge("note", note.id, "indicator", ioc["value"], "INDICATES")

    if verbose:
        print(f"  {hid} -> {note.id}  ({len(techs)} techniques, {len(extract_iocs(hunt['body']))} IOCs)")
    return note.id


def main():
    ap = argparse.ArgumentParser(description="Ingest ATHF hunts into ZettelForge")
    ap.add_argument("path", type=Path)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    paths = sorted(args.path.rglob("*.md")) if args.path.is_dir() else [args.path]
    hunts = [h for p in paths if (h := parse_hunt(p))]
    print(f"{len(hunts)} hunt(s) parsed")

    if args.dry_run:
        for h in hunts:
            fm = h["fm"]
            print(f"  {fm['hunt_id']}: {fm.get('title','?')}  techs={fm.get('techniques',[])}  iocs={len(extract_iocs(h['body']))}")
        return

    mm = get_memory_manager()
    ok = sum(1 for h in hunts if ingest(mm, h, verbose=args.verbose))
    print(f"Ingested {ok}/{len(hunts)} hunts into ZettelForge")


if __name__ == "__main__":
    main()
