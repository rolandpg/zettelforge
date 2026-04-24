# Human Evaluation Rubric for ZettelForge Briefings

**Purpose:** Structured monthly review process for random agent briefings to qualitatively assess ZettelForge's impact on CTI analysis quality.

**Frequency:** Monthly — use `scripts/human_eval_sampler.py` to select 20 random briefings from the past month's telemetry.

**Scale:** 1 (poor) to 5 (excellent) for each criterion.

---

## Evaluation Criteria

### 1. Recall Relevance (1-5)

Did the recall step surface relevant, high-quality notes?

- **5** — All retrieved notes are directly relevant to the query; no noise
- **4** — Most notes are relevant; 1-2 tangential results
- **3** — Mix of relevant and somewhat tangential notes
- **2** — Few relevant notes; mostly noise
- **1** — No useful notes retrieved

**What to check:**
- Are the retrieved notes about the right threat actors, TTPs, infrastructure?
- Does tier assignment make sense (tier A notes should be most relevant)?
- Are there obvious missed sources (e.g., missing MITRE techniques)?

### 2. Synthesis Value (1-5)

Was the synthesized briefing useful and actionable for CTI analysis?

- **5** — Briefing is clear, actionable, and well-structured
- **4** — Briefing is useful but could be tighter
- **3** — Briefing covers basics but lacks depth
- **2** — Briefing is superficial or poorly organized
- **1** — Briefing is misleading or unusable

**What to check:**
- Is the narrative coherent and logically structured?
- Does it answer the original query?
- Are key findings highlighted appropriately?

### 3. Critical Notes Missing (1-5)

Were any important notes not retrieved?

- **5** — No critical gaps; all known important notes were present
- **4** — Minor gaps only
- **3** — Some notable notes missing but not game-changing
- **2** — Several important notes missing
- **1** — Key evidence completely absent

**What to check:**
- Based on your knowledge of the topic, what should have been found?
- Would additional recall rounds have helped?
- Was the gap due to retrieval or due to no source notes existing?

### 4. Unsupported Claims (1-5)

Did the synthesis make claims not backed by the retrieved notes?

- **5** — All claims are directly supported by cited notes
- **4** — One minor unsupported inference
- **3** — Some claims stretch beyond source material
- **2** — Several unsupported claims; hallucination likely
- **1** — Briefing contains fabricated or misleading claims

**What to check:**
- Cross-reference each key claim against its cited note
- Look for "hallucination patterns": overly specific details not in source, contradictory attributions
- Check for conflation of different sources

### 5. Latency Perception (1-5)

Was the response time acceptable given the depth of analysis?

- **5** — Response was instant; no waiting
- **4** — Short wait (< 10s); acceptable for depth
- **3** — Moderate wait (10-30s); noticeable but tolerable
- **2** — Long wait (30-60s); frustrating for simple queries
- **1** — Very long wait (> 60s); feels broken

**What to check:**
- Is the latency reasonable for the query complexity?
- Where did most time go (recall, graph, synthesis)?
- Would parallelization or caching help?

### 6. Overall Trust (1-5)

Would you trust this briefing for operational CTI analysis?

- **5** — Would use verbatim in an operational report
- **4** — Would use with minor edits
- **3** — Would use as a draft requiring significant verification
- **2** — Would not trust without manual verification
- **1** — Cannot trust; would discard

**What to check:**
- Overall quality of the complete pipeline output
- Confidence vs. actual quality correlation
- Would you stake your reputation on this briefing?

---

## Scoring Summary

| Metric | Formula | Interpretation |
|--------|---------|---------------|
| **Quality Score** | avg(1-4) | >4.0 = excellent, >3.0 = usable, <3.0 = needs work |
| **Trust Rate** | count(6 >= 4) / N | % of briefings you'd trust operationally |
| **Hallucination Rate** | count(4 = 1 or 2) / N | % with unsupported claims |
| **Gap Rate** | count(3 <= 2) / N | % with critical missing notes |

---

## Human Evaluation Entry Schema

When Roland completes the review, append the evaluation to `~/.amem/telemetry/human_eval.jsonl`:

```json
{
  "event_type": "human_eval",
  "evaluated_at": "2026-04-23T14:30:00",
  "source_query": "APT28 infrastructure in Eastern Europe",
  "source_ts": "2026-04-22T08:15:00",
  "scores": {
    "recall_relevance": 4,
    "synthesis_value": 5,
    "critical_notes_missing": 4,
    "unsupported_claims": 5,
    "latency_perception": 3,
    "overall_trust": 5
  },
  "notes": "Excellent briefing. Minor latency issue but content was spot-on."
}
```
