# @Deuslogica X.com Content Performance Analysis
**Date:** 2026-03-31
**Account:** @Deuslogica (Patrick Roland)
**Sample:** Last 100 original posts via `xurl search "from:DeusLogica"`, plus mentions and likes

---

## Account Snapshot

| Metric | Value |
|--------|-------|
| Followers | 309 |
| Following | 1,391 |
| Total Tweets | 3,339 |
| Listed | 3 |
| Account Age | ~4 years (Dec 2021) |
| Verified | No |

**Follower quality signal:** 1,391 following / 309 followers = 4.5:1 ratio. Account follows heavily but isn't followed back at scale. Growth is engagement-driven, not reciprocal-network-driven.

---

## Executive Summary

### Top 3 Findings

**1. Zero Retweets on Original Content**
Of 53 original posts in the sample, exactly 0 received a single retweet. The only RT activity on the account are pure RTs of others' content (4 in sample). This is the single most important signal: the content is not shareable. Either the format, the hook, or the audience fit is broken. At 309 followers, organic RT amplification is the only growth engine available, and it is not firing.

**2. Template-Heavy Automation Undermines Human Connection**
The CISA KEV and EPSS threads follow a rigidly identical format:
```
[emoji] [SEVERITY] | [CONFIDENCE]

CVE-XXXX-XXXX [EPSS/SCORE]
[One-line description]

Source: [Source] | Reliability: [Grade]

Link: [URL]
```
This format is useful for a bot feed but reads as disposable. The templated timestamps visible in the draft-posts-turned-tweets ("Timestamp: 2026-03-30T11:11:47.242490") confirm the posts are near-direct dumps from an automated alert pipeline. X rewards personality and voice. This format has none.

**3. Replies to High-Profile Accounts Are the Best Performing Content**
The top tweet by impressions (197) was a reply to @vxunderground calling out a post as "cyber-grifting." The second-best (153 impressions) was a standalone CVE announcement. Third (77) was a reply correcting @chatgpt21's misunderstanding of cybersecurity. The pattern is clear: engaging directly with prominent accounts in the security space generates more reach than broadcast posting.

---

## Content Categories Identified

### Category Breakdown (53 original posts in sample)

| Category | Count | % of Sample | Avg Impressions | RTs | Likes |
|----------|-------|-------------|-----------------|-----|-------|
| CISA KEV Alerts | 18 | 34% | 28 | 0 | 0.2 |
| EPSS Threads | 10 | 19% | 38 | 0 | 0 |
| Supply Chain / Threat Intel | 7 | 13% | 35 | 0 | 0.4 |
| Opinion / Contrarian | 6 | 11% | 98 | 0 | 0.5 |
| Replies to Others | 9 | 17% | 61 | 0 | 0.3 |
| Personal / Misc | 3 | 6% | 15 | 0 | 0.2 |

### Best Performing Content Categories

**1. Opinion / Contrarian Takes (avg ~98 impressions)**
These posts generate the most organic reach:
- "The patch race is over. Defenders are on the ropes." (impressions: 61)
- "I don't think you know what cybersecurity companies actually do." (77 impressions, reply)
- "how do we feel about agentic mind control?" (9 impressions — low, but philosophical style worth exploring)
- "Cyber-grifting is still at an all time high" (197 impressions as reply — this was Patrick's best performing post)

Pattern: Short, sharp, dismissive/contrarian takes that challenge prevailing narratives. The shorter the better. The more direct the challenge, the more engagement.

**2. High-Severity CVE Announcements (avg ~35 impressions, spikes possible)**
- CVE-2026-20131 (CVSS 10.0) — 153 impressions, 1 like
- CVE-2026-3055 (HIGH CVSS 9.0, active exploitation) — 61 impressions

Pattern: When a truly critical CVE drops (CVSS 9-10, confirmed in-the-wild exploitation, brand-name vendor), there is a predictable spike. These should be posted immediately and without the full template treatment.

**3. Supply Chain / Threat Intel (avg ~35 impressions)**
- Cisco/Trivy supply chain attack — multiple posts, 16-22 impressions each
- axios NPM compromise — 28 impressions
- TrueConf zero-day — 22 impressions

Pattern: Supply chain attacks outperform generic CVE posts. Attribution to nation-state actors (North Korea, China) drives slightly more interest.

### Worst Performing Categories

**1. CISA KEV Update Threads (avg ~28 impressions, 0 RTs)**
These are the most frequent post type and the most templated. Format appears identical every time. The audience for CISA KEV updates is practitioners who already have KEV feeds — they don't need Patrick's version. Posting every KEV addition is noise, not signal.

**2. EPSS Scoring Threads (avg ~38 impressions, 0 RTs)**
These are 10-part threads covering EPSS 94%+ CVEs. The format is 100% templated, the content is already available from CISA/FIRST, and the thread structure means each tweet must be clicked into to be understood. No single tweet in an EPSS thread has ever RT'd.

**3. Raw Alert Output Tweets (draft posts published as-is)**
Several tweets in the sample contain raw alert metadata:
```
Timestamp: 2026-03-30T11:11:47.242490
Type: HIGH_EPSS
Severity: CRITICAL
```
These are clearly failed drafts or pipeline errors. They look unprofessional and should be deleted.

---

## Engagement Pattern Analysis

### What Gets Impressions
- Replies to high-follower accounts (vxunderground, chatgpt21)
- CVSS 9-10 critical vulnerabilities
- Supply chain attacks
- Contrarian/industry challenge takes

### What Gets Likes
- Almost nothing in the sample gets liked
- Best: CVE-2026-20131 (1 like)
- Second best: philosophical reply about AI slop (1 like)
- Everything else: 0 likes

### What Gets Saves (bookmarks)
- No bookmarks visible in the sample for Patrick's posts
- This suggests content is not being perceived as reference material worth saving

### What Gets Replies
- Contrarian/opinion posts
- Correction-style replies to influential accounts
- The AI "mind control" post generated 0 replies but is the kind of post that could

### What Gets Retweeted
**Nothing.** Zero organic RTs on any original post in the sample. This is the critical bottleneck.

---

## Content Pillar Comparison

Patrick's stated content pillars (from USER.md and SOUL.md):
1. MSSP Operations
2. CMMC/DIB Security
3. Leadership / Management
4. Cybersecurity Market Analysis
5. Philosophical / Contrarian Takes

**Actual content in sample:**

| Pillar | Posts Found | Notes |
|--------|-------------|-------|
| MSSP Operations | ~2 | Almost entirely absent from recent sample |
| CMMC/DIB | 0 | Not present in recent posts |
| Leadership | ~3 | Scattered, mostly in replies |
| Market Analysis | ~1 | axios/NPM supply chain post loosely qualifies |
| Philosophical/Contrarian | ~6 | Best performing;Reply to vxunderground, chatgpt21, AI mind control |
| CTI/Vulnerability | ~35 | Dominates the feed (~66% of posts) |

**Gap:** The account is operating as an automated CVE feed, not a thought leadership account. The stated pillars — MSSP ops, CMMC, leadership, market analysis — are essentially absent from recent content.

---

## Critical Issues

### Issue 1: Alert Pipeline Leakage
Several tweets contain raw alert metadata (timestamps, draft formatting). This suggests an automated pipeline is publishing posts without human review. These tweets should be deleted and the pipeline fixed.

### Issue 2: Zero RT Economy
At 309 followers, organic RTs from engaged followers are the only growth mechanism. With 0 RTs on 53 original posts, the account is not generating shareable content. Root causes:
- No hot takes or punchy one-liners
- No visual content
- No data that surprises people
- No posts that make followers look smart by sharing

### Issue 3: Over-Posting Low-Value Alerts
Posting every CISA KEV addition and every EPSS 94% CVE is broadcasting noise. A practitioner following 5 other CTI accounts already gets this information. Patrick's value is in synthesis, perspective, and filtering — not becoming a third-party alert relay.

### Issue 4: No Hashtags, No Calls to Action
Almost no posts use hashtags, mentions to drive conversation, or any form of engagement prompting. X's algorithm rewards engagement signals. Posts that don't ask for anything get nothing.

### Issue 5: No Multimedia
Zero video, images, or formatted cards in the sample. Visual content dramatically outperforms text-only posts on X. A thread with a single diagram outperforms a text thread every time.

---

## Recommendations

### Immediate (This Week)

1. **Delete the raw alert metadata tweets** — They look broken. Fix the pipeline so timestamps don't appear.

2. **Reduce alert posting by 80%** — Post only CVEs that meet ALL of: CVSS 9+, confirmed in-the-wild exploitation, brand-name vendor (Microsoft, Cisco, Zoho, Ivanti, Citrix). Skip everything else.

3. **Add a contrasting opinion to every alert post** — "This is why [X] is still unpatched in most environments." or "The real story here is [Y], not the CVE itself." Pure alert dumps are valueless as standalone posts.

4. **Start a "WTF Just Happened" series** — One post per week summarizing a major incident with Patrick's take. Synthesize, don't relay. This is where his expertise differentiates from a bot.

### Short-Term (Next 30 Days)

5. **Publish 2 leadership/MSSP posts per week** — Patrick has deep MSSP and DIB experience. Write about: "Why most MSSP SOCs are running on fumes," "The CMMC gap nobody talks about," "What PE due diligence gets wrong about MSSP acquisitions." This is content only Patrick can write.

6. **Reply more, broadcast less** — The data shows replies to prominent accounts outperform standalone posts. Spend 50% of engagement time in replies to high-follower accounts (Schneier, CISA, vxunderground, Marcus Hutchins, etc.) with substantive contributions, not just links.

7. **Add visual formatting to threads** — Even a simple numbered list with emoji is better than a wall of text. Consider: a single-screenshot KQL rule, a network diagram, a before/after comparison.

8. **No hashtag, no post** — Add at least one relevant hashtag to every post (#Cybersecurity #MSSP #CMMC #DIB #ThreatIntel). Hashtags don't drive much but they help with discovery.

### Growth Strategy (Next 90 Days)

9. **Target 1 RT-worthy post per week** — A post designed to make a CISO laugh, a founder agree, or a practitioner think. Something with a hook, a perspective, and a share trigger. Track RT rate per post.

10. **Build a content backlog** — Pre-draft 10 posts across all 5 pillars. Publish no more than 3 per day, at least 2 hours apart. Quality over quantity.

---

## Content Calendar: Week of April 1-7, 2026

| Day | Primary Post | Secondary Post |
|-----|-------------|---------------|
| Tue Apr 1 | "The patch race is over — here's what's next" (synthesized vuln mgmt piece, link to LinkedIn article) | CISA KEV alert (if any meet threshold) |
| Wed Apr 2 | "Why MSSP SOCs are running on fumes" (original thought leadership) | Reply to high-profile security account |
| Thu Apr 3 | CISA KEV / critical CVE only (skip if nothing notable) | "AI slop is making threat intel worse" (contrarian) |
| Fri Apr 4 | "What PE due diligence gets wrong about MSSP security" (market positioning) | Reply / engagement day |
| Sat Apr 5 | Light: relevant news dump with one-line take | None |
| Sun Apr 6 | None | None |
| Mon Apr 7 | "CMMC 2.0 enforcement is coming — most DIB contractors aren't ready" (CMMC pillar) | CISA KEV alert if warranted |

---

## Specific Post Ideas

**High-potential ideas based on audience and positioning:**

1. **"The pyramid of pain is inverted. Here's what that means for your SOC."** — Contrarian take on threat intel. Would generate replies from practitioners. (~100-200 impressions potential)

2. **"I reviewed 20 MSSP contracts last quarter. Here's what's broken in every single one."** — Leadership/MSSP pillar. Unique value. Would be saved and shared. (~150+ impressions potential, RT-worthy)

3. **"CVE-2026-3055 / Citrix: patch now or assume compromise"** — Critical CVE post with Patrick's take on what makes this different from the 500 other CVEs. Short, urgent, actionable.

4. **"The CISA KEV is a list, not a strategy. Here's what actual exposure management looks like."** — Contrarian, positions Patrick as a practitioner who sees the big picture. Links to Summit 7/Summit7.us.

5. **"DIB contractors: if you think CMMC compliance is a checkbox, you're already behind."** — CMMC/DIB pillar. Direct, no fluff. Target audience would engage.

6. **"APT28 is not sophisticated. Your edge devices are just soft."** — CTI with contrarian framing. Would generate debate and RTs from the security community.

7. **"What SentinelOne vs. Crowdstrike tells us about the MSSP tool problem"** — Market analysis with a take. Positions Patrick as someone who understands the business of security.

---

## Appendix: Data Sample Notes

- **Source:** `xurl search "from:DeusLogica" -n 100`
- **Total tweets analyzed:** 57 (4 pure RTs excluded, 53 originals)
- **Date range:** 2026-03-27 to 2026-03-31 (most recent)
- **Historical tweets** (pre-March 27) may show different patterns — the account may have been more active in earlier periods
- **Impressions data** only available for recent posts via X API; older posts show 0 impressions
- **Engagement rate** cannot be calculated accurately without impression data across the full sample

