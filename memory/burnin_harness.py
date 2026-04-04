#!/usr/bin/env python3
"""
Burn-In Harness — 30-Day Operational Test for ThreatRecall
===========================================================

Wraps mm.remember() with comprehensive instrumentation for
production-ready metrics and quality validation.

Usage:
    from burnin_harness import BurnInHarness
    from memory_manager import get_memory_manager

    mm = get_memory_manager()
    harness = BurnInHarness(mm=mm, log_dir="burnin/logs", report_dir="burnin/reports")

    # Ingest threat intel
    result = harness.ingest(
        content="Full threat intelligence report...",
        source_type="cisa_advisory",
        source_ref="CISA-AA26-091A",
        source_url="https://www.cisa.gov/advisories/AA26-091A"
    )

    # At end of day
    harness.daily_summary()

    # Weekly reports
    harness.weekly_report(week_number=1)
"""

import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from functools import wraps
import threading

# Setup paths
MEMORY_DIR = Path("/home/rolandpg/.openclaw/workspace/memory")
sys.path.insert(0, str(MEMORY_DIR))

from memory_manager import get_memory_manager


# =============================================================================
# Tier Assignment Mappings (from PRD Section 4.2)
# =============================================================================

TIER_A_SOURCE_TYPES = {
    "cisa_advisory",
    "mitre_update",
    "vendor_bulletin",
    "nvd_entry",
    "first_iep",
    "human",
    "tool",
    "observation",
    "ingestion",
    "manual",
    "briefing",
    "advisory",
    "cisa_advisory",
}

TIER_B_SOURCE_TYPES = {
    "threat_report",
    "otx_pulse",
    "research_paper",
    "security_blog",
    "agent",
    "conversation",
    "cti_ingestion",
    "subagent_output",
    "task_output",
}

TIER_C_SOURCE_TYPES = {
    "rss_article",
    "darkweb_scan",
    "social_media",
    "community_report",
    "agent_summary",
    "summary",
    "synthesis",
    "generated",
    "review",
}


class BurnInResult:
    """Result of a single burn-in ingestion operation."""

    def __init__(
        self,
        content_preview: str,
        source_type: str,
        source_ref: str,
        source_url: Optional[str],
        note_id: Optional[str],
        status: str,  # "created", "duplicate_skipped", "error"
        reason: str = "",
        entities_extracted: int = 0,
        entities_resolved: int = 0,
        tier: Optional[str] = None,
        links_generated: int = 0,
        evolution_triggered: bool = False,
        evolution_decision: Optional[str] = None,
        latency_ms: float = 0.0,
        error: Optional[str] = None,
    ):
        self.content_preview = content_preview[:200] if content_preview else ""
        self.source_type = source_type
        self.source_ref = source_ref
        self.source_url = source_url
        self.note_id = note_id
        self.status = status
        self.reason = reason
        self.entities_extracted = entities_extracted
        self.entities_resolved = entities_resolved
        self.tier = tier
        self.links_generated = links_generated
        self.evolution_triggered = evolution_triggered
        self.evolution_decision = evolution_decision
        self.latency_ms = latency_ms
        self.error = error
        self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp,
            "content_preview": self.content_preview,
            "source_type": self.source_type,
            "source_ref": self.source_ref,
            "source_url": self.source_url,
            "note_id": self.note_id,
            "status": self.status,
            "reason": self.reason,
            "entities_extracted": self.entities_extracted,
            "entities_resolved": self.entities_resolved,
            "tier": self.tier,
            "links_generated": self.links_generated,
            "evolution_triggered": self.evolution_triggered,
            "evolution_decision": self.evolution_decision,
            "latency_ms": round(self.latency_ms, 3),
            "error": self.error,
        }


class BurnInStats:
    """Cumulative statistics for burn-in period."""

    def __init__(self):
        self.notes_attempted = 0
        self.notes_stored = 0
        self.notes_deduplicated = 0
        self.notes_errored = 0
        self.total_latency_ms = 0.0
        self.entity_counts: Dict[str, int] = {"extracted": 0, "resolved": 0}
        self.tier_counts: Dict[str, int] = {}
        self.source_counts: Dict[str, int] = {}
        self.link_counts: Dict[str, int] = {}
        self.evolution_counts: Dict[str, int] = {"triggered": 0, "no_change": 0}
        self.errors: List[Dict] = []
        self.alias_gaps: List[Dict] = []
        self.start_time = datetime.now()

    def record_success(self, result: BurnInResult):
        self.notes_attempted += 1
        self.notes_stored += 1
        self.total_latency_ms += result.latency_ms
        self.entity_counts["extracted"] += result.entities_extracted
        self.entity_counts["resolved"] += result.entities_resolved
        self.tier_counts[result.tier or "unknown"] = self.tier_counts.get(
            result.tier or "unknown", 0
        ) + 1
        self.source_counts[result.source_type] = self.source_counts.get(
            result.source_type, 0
        ) + 1
        self.link_counts["generated"] = self.link_counts.get("generated", 0) + result.links_generated

        if result.evolution_triggered:
            self.evolution_counts["triggered"] += 1
            self.evolution_counts[result.evolution_decision or "unknown"] = (
                self.evolution_counts.get(result.evolution_decision or "unknown", 0) + 1
            )

    def record_dedup(self, result: BurnInResult):
        self.notes_attempted += 1
        self.notes_deduplicated += 1

    def record_error(self, result: BurnInResult):
        self.notes_attempted += 1
        self.notes_errored += 1
        self.errors.append(
            {
                "timestamp": result.timestamp,
                "source_type": result.source_type,
                "source_ref": result.source_ref,
                "error": result.error or "unknown error",
            }
        )


class BurnInHarness:
    """
    Burn-in harness that wraps memory operations with instrumentation.

    Usage:
        harness = BurnInHarness(mm=mm, log_dir="burnin/logs", report_dir="burnin/reports")
        result = harness.ingest(content, source_type, source_ref, source_url)
        harness.daily_summary()
    """

    def __init__(
        self,
        mm: Optional[Any] = None,
        log_dir: str = "burnin/logs",
        report_dir: str = "burnin/reports",
    ):
        self.mm = mm or get_memory_manager()
        self.log_dir = Path(log_dir)
        self.report_dir = Path(report_dir)
        self.stats = BurnInStats()
        self.current_day = datetime.now().strftime("%Y-%m-%d")

        # Create directories
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.report_dir.mkdir(parents=True, exist_ok=True)

        # Daily log file
        self.daily_log_path = self.log_dir / f"{self.current_day}.jsonl"

    def _get_tier(self, source_type: str) -> str:
        """Determine tier from source_type."""
        if source_type in TIER_A_SOURCE_TYPES:
            return "A"
        elif source_type in TIER_B_SOURCE_TYPES:
            return "B"
        elif source_type in TIER_C_SOURCE_TYPES:
            return "C"
        return "B"  # Default

    def ingest(
        self,
        content: str,
        source_type: str,
        source_ref: str,
        source_url: Optional[str] = None,
        auto_evolve: bool = True,
    ) -> BurnInResult:
        """
        Ingest content through the memory pipeline with full instrumentation.

        auto_evolve: Run evolution cycle after each note (default True). Set False
        for high-volume batch ingestion where evolution will be run separately.

        Returns BurnInResult with timing, entity extraction, dedup, evolution info.
        """
        start_time = time.time()
        tier = self._get_tier(source_type)

        try:
            note, reason = self.mm.remember(
                content=content,
                source_type=source_type,
                source_ref=source_ref,
                domain="security_ops",
                auto_evolve=auto_evolve,
                force=False,
            )

            latency_ms = (time.time() - start_time) * 1000

            # Extract entity information
            entities_extracted = 0
            entities_resolved = 0

            # Parse reason for dedup info
            status = "created"
            if reason and reason.startswith("duplicate_skipped"):
                status = "duplicate_skipped"
                reason_parts = reason.split(":")
                if len(reason_parts) > 1:
                    reason = reason_parts[1]

            # Try to extract entity info from note if created
            entities_extracted = 0
            entities_resolved = 0
            links_generated = 0
            evolution_triggered = False
            evolution_decision = None

            if note:
                # Count entities in semantic field
                entities_extracted = len(note.semantic.entities) if note.semantic else 0

                # Count links
                if hasattr(note, "links") and note.links:
                    links_generated = len(note.links.related)

                # Get evolution info from metadata
                evolution_triggered = note.metadata.evolution_count > 0 if note.metadata else False
                evolution_decision = self._get_evolution_decision_from_reason(reason)

            result = BurnInResult(
                content_preview=content,
                source_type=source_type,
                source_ref=source_ref,
                source_url=source_url,
                note_id=note.id if note else None,
                status=status,
                reason=reason,
                entities_extracted=entities_extracted,
                entities_resolved=entities_resolved,
                tier=tier,
                links_generated=links_generated,
                evolution_triggered=evolution_triggered,
                evolution_decision=evolution_decision,
                latency_ms=latency_ms,
            )

            if status == "created":
                self.stats.record_success(result)
            elif status == "duplicate_skipped":
                self.stats.record_dedup(result)

            # Log to daily file
            self._log_result(result)

            return result

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            result = BurnInResult(
                content_preview=content,
                source_type=source_type,
                source_ref=source_ref,
                source_url=source_url,
                note_id=None,
                status="error",
                reason="",
                entities_extracted=0,
                entities_resolved=0,
                tier=tier,
                latency_ms=latency_ms,
                error=str(e),
            )
            self.stats.record_error(result)
            self._log_result(result)
            return result

    def _get_evolution_decision_from_reason(self, reason: str) -> Optional[str]:
        """Extract evolution decision from memory_manager reason strings."""
        if "SUPERSEDE" in reason.upper():
            return "SUPERSEDE"
        elif "REJECT" in reason.upper():
            return "REJECT"
        elif "UPDATE" in reason.upper():
            if "UPDATE_CONTEXT" in reason.upper():
                return "UPDATE_CONTEXT"
            elif "UPDATE_TAGS" in reason.upper():
                return "UPDATE_TAGS"
            elif "UPDATE_BOTH" in reason.upper():
                return "UPDATE_BOTH"
            return "UPDATE"
        elif "NO_CHANGE" in reason.upper():
            return "NO_CHANGE"
        return None

    def _log_result(self, result: BurnInResult):
        """Append result to daily log file."""
        with open(self.daily_log_path, "a") as f:
            f.write(json.dumps(result.to_dict()) + "\n")

    def _load_results(self) -> List[BurnInResult]:
        """Load all results from daily log file."""
        results = []
        if not self.daily_log_path.exists():
            return results

        with open(self.daily_log_path, "r") as f:
            for line in f:
                if line.strip():
                    try:
                        data = json.loads(line)
                        result = BurnInResult(
                            content_preview=data.get("content_preview", ""),
                            source_type=data.get("source_type", ""),
                            source_ref=data.get("source_ref", ""),
                            source_url=data.get("source_url"),
                            note_id=data.get("note_id"),
                            status=data.get("status", ""),
                            reason=data.get("reason", ""),
                            entities_extracted=data.get("entities_extracted", 0),
                            entities_resolved=data.get("entities_resolved", 0),
                            tier=data.get("tier"),
                            links_generated=data.get("links_generated", 0),
                            evolution_triggered=data.get("evolution_triggered", False),
                            evolution_decision=data.get("evolution_decision"),
                            latency_ms=data.get("latency_ms", 0.0),
                            error=data.get("error"),
                        )
                        results.append(result)
                    except json.JSONDecodeError:
                        continue

        return results

    def daily_summary(self) -> Dict:
        """Generate and print daily summary report."""
        results = self._load_results()

        print(f"\n{'='*60}")
        print(f"BURN-IN DAILY SUMMARY - {self.current_day}")
        print(f"{'='*60}")

        # Basic counts
        notes_attempted = len(results)
        created = sum(1 for r in results if r.status == "created")
        deduped = sum(1 for r in results if r.status == "duplicate_skipped")
        errored = sum(1 for r in results if r.status == "error")

        print(f"\nIngestion Metrics:")
        print(f"  Notes attempted:   {notes_attempted}")
        print(f"  Successfully saved: {created}")
        print(f"  Deduplicated:      {deduped}")
        print(f"  Errors:            {errored}")

        if notes_attempted > 0:
            dedup_rate = (deduped / notes_attempted) * 100
            print(f"  Dedup rate:        {dedup_rate:.1f}%")

        # Latency stats
        latencies = [r.latency_ms for r in results if r.latency_ms > 0]
        if latencies:
            avg_lat = sum(latencies) / len(latencies)
            p50 = sorted(latencies)[len(latencies) // 2]
            p95 = sorted(latencies)[int(len(latencies) * 0.95)] if len(latencies) > 1 else p50
            p99 = sorted(latencies)[int(len(latencies) * 0.99)] if len(latencies) > 1 else p50
            max_lat = max(latencies)

            print(f"\nLatency (ms):")
            print(f"  Avg:  {avg_lat:.1f}")
            print(f"  P50:  {p50:.1f}")
            print(f"  P95:  {p95:.1f}")
            print(f"  P99:  {p99:.1f}")
            print(f"  Max:  {max_lat:.1f}")

        # Entity extraction
        total_extracted = sum(r.entities_extracted for r in results)
        total_resolved = sum(r.entities_resolved for r in results)

        print(f"\nEntity Extraction:")
        print(f"  Total extracted: {total_extracted}")
        print(f"  Total resolved:  {total_resolved}")

        # Tier distribution
        tiers = {}
        for r in results:
            if r.tier:
                tiers[r.tier] = tiers.get(r.tier, 0) + 1

        print(f"\nTier Distribution:")
        for tier in ["A", "B", "C"]:
            count = tiers.get(tier, 0)
            pct = (count / len(results) * 100) if results else 0
            print(f"  Tier {tier}: {count} ({pct:.1f}%)")

        # Source types
        sources = {}
        for r in results:
            sources[r.source_type] = sources.get(r.source_type, 0) + 1

        print(f"\nSource Types:")
        for src, count in sorted(sources.items(), key=lambda x: x[1], reverse=True)[:10]:
            pct = (count / len(results) * 100) if results else 0
            print(f"  {src}: {count} ({pct:.1f}%)")

        # Evolution stats
        evolutions = {}
        for r in results:
            if r.evolution_decision:
                evolutions[r.evolution_decision] = evolutions.get(r.evolution_decision, 0) + 1

        print(f"\nEvolution Decisions:")
        for decision in ["NO_CHANGE", "UPDATE_CONTEXT", "UPDATE_TAGS", "UPDATE_BOTH", "SUPERSEDE", "REJECT"]:
            count = evolutions.get(decision, 0)
            if count > 0:
                print(f"  {decision}: {count}")

        # Check for issues
        print(f"\nQuality Checks:")

        # Check for 0 entity extraction
        no_entities = [r for r in results if r.entities_extracted == 0 and r.status == "created"]
        if no_entities:
            print(f"  WARNING: {len(no_entities)} notes with 0 entities extracted")
            for r in no_entities[:3]:
                print(f"    - {r.source_ref}: {r.content_preview[:50]}...")

        # Check for errors
        if errored > 0:
            print(f"  ERROR: {errored} notes failed to ingest")
            for err in self.stats.errors[-5:]:
                print(f"    - {err['source_ref']}: {err['error'][:100]}")

        # Save summary
        summary = {
            "date": self.current_day,
            "notes_attempted": notes_attempted,
            "notes_stored": created,
            "notes_deduplicated": deduped,
            "notes_errored": errored,
            "latency_avg_ms": round(avg_lat, 2) if latencies else 0,
            "tier_distribution": tiers,
            "source_distribution": sources,
            "evolution_decisions": evolutions,
        }

        summary_path = self.report_dir / f"summary_{self.current_day}.json"
        with open(summary_path, "w") as f:
            json.dump(summary, f, indent=2)

        print(f"\nSummary saved to: {summary_path}")
        print(f"{'='*60}\n")

        return summary

    def weekly_report(self, week_number: int = 1) -> Dict:
        """Generate weekly cumulative report."""
        print(f"\n{'='*60}")
        print(f"BURN-IN WEEKLY REPORT - Week {week_number}")
        print(f"{'='*60}")

        # Load all results from all days this week
        all_results = []
        day = datetime.now()
        for i in range((day.weekday() + 1) % 7 + (week_number - 1) * 7, (day.weekday() + 1) % 7 + week_number * 7):
            if i < 7:
                date = (day - timedelta(days=i)).strftime("%Y-%m-%d")
                log_path = self.log_dir / f"{date}.jsonl"
                if log_path.exists():
                    with open(log_path, "r") as f:
                        for line in f:
                            if line.strip():
                                try:
                                    all_results.append(json.loads(line))
                                except json.JSONDecodeError:
                                    continue

        if not all_results:
            print("No results found for this week period")
            return {}

        total = len(all_results)
        created = sum(1 for r in all_results if r.get("status") == "created")
        deduped = sum(1 for r in all_results if r.get("status") == "duplicate_skipped")
        errored = sum(1 for r in all_results if r.get("status") == "error")

        latencies = [r.get("latency_ms", 0) for r in all_results if r.get("latency_ms", 0) > 0]
        avg_lat = sum(latencies) / len(latencies) if latencies else 0

        print(f"\nWeekly Cumulative Metrics:")
        print(f"  Total notes attempted: {total}")
        print(f"  Successfully stored:   {created}")
        print(f"  Deduplicated:          {deduped}")
        print(f"  Errors:                {errored}")
        print(f"  Dedup rate:            {(deduped/total*100):.1f}%" if total > 0 else "N/A")
        print(f"  Avg latency:           {avg_lat:.1f}ms")

        # Save weekly report
        report = {
            "week": week_number,
            "period_start": (datetime.now() - timedelta(days=(week_number-1)*7)).strftime("%Y-%m-%d"),
            "period_end": datetime.now().strftime("%Y-%m-%d"),
            "total_notes": total,
            "stored": created,
            "deduplicated": deduped,
            "errors": errored,
            "avg_latency_ms": round(avg_lat, 2),
            "daily_breakdown": {},
        }

        # Group by day
        daily = {}
        for r in all_results:
            date = r.get("timestamp", "")[:10]
            if date not in daily:
                daily[date] = 0
            daily[date] += 1
        report["daily_breakdown"] = daily

        report_path = self.report_dir / f"weekly_{week_number}.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)

        print(f"\nWeekly report saved to: {report_path}")
        print(f"{'='*60}\n")

        return report

    def validate_cross_alias_recall(
        self, actor_aliases: Dict[str, List[str]]
    ) -> Dict[str, Dict]:
        """
        Validate cross-alias recall for specified actors.

        actor_aliases: {"actor_name": ["alias1", "alias2", ...]}
        """
        results = {}

        for actor_name, aliases in actor_aliases.items():
            all_note_sets = []
            for alias in aliases:
                notes = self.mm.recall_actor(alias, k=10, exclude_superseded=True)
                note_ids = {n.id for n in notes}
                all_note_sets.append(note_ids)

            # Check if all aliases return same set
            if len(all_note_sets) > 1:
                all_equal = all(s == all_note_sets[0] for s in all_note_sets[1:])
            else:
                all_equal = True

            results[actor_name] = {
                "aliases_tested": len(aliases),
                "note_count_per_alias": [len(s) for s in all_note_sets],
                "all_aliases_return_same": all_equal,
                "note_sets": [list(s) for s in all_note_sets],
            }

            # Record alias gaps
            if not all_equal:
                for i, (alias, notes) in enumerate(zip(aliases, all_note_sets)):
                    missing_from_others = []
                    for j, other_set in enumerate(all_note_sets):
                        if i != j:
                            diff = notes - other_set
                            if diff:
                                missing_from_others.append((aliases[j], len(diff)))
                    if missing_from_others:
                        for other_alias, count in missing_from_others:
                            self.stats.alias_gaps.append({
                                "actor": actor_name,
                                "alias": alias,
                                "missing_from": other_alias,
                                "missing_count": count,
                            })

        return results

    def validate_epistemic_integrity(self) -> Dict:
        """
        Validate that Tier C notes do not trigger evolution of Tier A notes.
        """
        from reasoning_logger import get_reasoning_logger

        logger = get_reasoning_logger()
        reasoning = logger.get_recent(limit=1000)

        tier_a_notes = {}
        tier_c_notes = {}

        # Categorize notes by tier
        for r in reasoning:
            if r.get("event_type") == "tier_assignment":
                note_id = r.get("note_id")
                tier = r.get("tier")
                if tier == "A":
                    tier_a_notes[note_id] = r
                elif tier == "C":
                    tier_c_notes[note_id] = r

        # Check for C->A evolution attempts
        violations = []
        for r in reasoning:
            if r.get("event_type") == "evolution_decision":
                new_tier = r.get("tier")
                decision = r.get("decision")

                if new_tier in ["B", "C"] and decision in ["SUPERSEDE", "UPDATE_BOTH", "UPDATE_CONTEXT", "UPDATE_TAGS"]:
                    # This is a potential violation - C or B trying to evolve A
                    violations.append({
                        "note_id": r.get("note_id"),
                        "new_tier": new_tier,
                        "decision": decision,
                        "reason": r.get("reason", ""),
                    })

        # Check reasoning log for REJECT events (good - shows tier enforcement working)
        rejects = [r for r in reasoning if r.get("event_type") == "evolution_decision" and r.get("decision") == "REJECT"]

        return {
            "tier_a_notes": len(tier_a_notes),
            "tier_c_notes": len(tier_c_notes),
            "violations_found": len(violations),
            "violations": violations[:10],  # First 10 violations
            "reject_count": len(rejects),
            "reject_examples": rejects[:5] if rejects else [],
        }


def run_burn_in_test(mm=None) -> BurnInHarness:
    """Quick burn-in test to verify harness works."""
    mm = mm or get_memory_manager()
    harness = BurnInHarness(mm=mm)

    print("Running burn-in test...")
    print()

    # Test data
    test_data = [
        {
            "content": "CISA issued advisory AA26-091A about Log4j vulnerability in web servers.",
            "source_type": "cisa_advisory",
            "source_ref": "CISA-AA26-091A",
            "source_url": "https://www.cisa.gov/advisories/AA26-091A",
        },
        {
            "content": "MuddyWater APT targeting Middle East with phishing campaigns.",
            "source_type": "otx_pulse",
            "source_ref": "otx_pulse_123",
            "source_url": "https://otx.alienvault.com/pulse/123",
        },
        {
            "content": "Community report: suspected Cobalt Strike beacon on port 443.",
            "source_type": "community_report",
            "source_ref": "community_456",
        },
        {
            "content": "CISA issued advisory AA26-091A about Log4j vulnerability in web servers.",
            "source_type": "cisa_advisory",
            "source_ref": "CISA-AA26-091A-DUP",
            "source_url": "https://www.cisa.gov/advisories/AA26-091A",
        },
    ]

    for data in test_data:
        result = harness.ingest(
            content=data["content"],
            source_type=data["source_type"],
            source_ref=data["source_ref"],
            source_url=data.get("source_url"),
        )
        print(f"  {result.source_ref}: {result.status} (tier={result.tier})")

    print()
    harness.daily_summary()

    return harness


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Burn-in harness for ThreatRecall")
    parser.add_argument("--quick-test", action="store_true", help="Run quick test with sample data")
    parser.add_argument("--ingest", type=str, help="Ingest content from file")
    parser.add_argument("--source-type", type=str, default="community_report", help="Source type for --ingest")
    parser.add_argument("--source-ref", type=str, default="cli", help="Source reference")
    parser.add_argument("--summary", action="store_true", help="Print daily summary")
    parser.add_argument("--weekly", type=int, help="Generate weekly report for week number")
    parser.add_argument("--validate-epistemic", action="store_true", help="Validate epistemic integrity")
    args = parser.parse_args()

    mm = get_memory_manager()

    if args.quick_test:
        harness = run_burn_in_test(mm)
    elif args.ingest:
        with open(args.ingest) as f:
            content = f.read()
        harness = BurnInHarness(mm=mm)
        result = harness.ingest(
            content=content,
            source_type=args.source_type,
            source_ref=args.source_ref,
        )
        print(f"Result: {result.status}")
        print(f"Note ID: {result.note_id}")
        print(f"Tier: {result.tier}")
    elif args.summary:
        harness = BurnInHarness(mm=mm)
        harness.daily_summary()
    elif args.weekly:
        harness = BurnInHarness(mm=mm)
        harness.weekly_report(args.weekly)
    elif args.validate_epistemic:
        harness = BurnInHarness(mm=mm)
        result = harness.validate_epistemic_integrity()
        print(json.dumps(result, indent=2))
    else:
        parser.print_help()
