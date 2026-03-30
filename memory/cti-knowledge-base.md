# CTI Knowledge Base — Patton's Reference
# Sources: FIRST.org CTI-SIG Curriculum, MITRE, NIST, Threat Intelligence Handbook
# Last updated: 2026-03-20

## Strategic vs Operational vs Tactical CTI

### Strategic CTI
- **Audience:** C-suite, board, senior leadership
- **Purpose:** Inform long-term security strategy and investment decisions
- **Time horizon:** Months to years
- **Examples:** "Ransomware groups increasingly targeting healthcare" / "APT29 shifting to supply chain focus"
- **Product formats:** White papers, risk assessments, annual reports

### Operational CTI
- **Audience:** Security operations leads, incident response managers
- **Purpose:** Guide day-to-day security operations and resource allocation
- **Time horizon:** Days to weeks
- **Examples:** "This actor group is currently active against defense contractors" / "New banking trojan variant spreading via spear-phishing"
- **Product formats:** Intelligence briefings, actor profiles, threat assessments

### Tactical CTI
- **Audience:** Detection engineers, SOC analysts, DFIR teams
- **Purpose:** Enable specific defensive actions — detection rules, hunting queries, blocking
- **Time horizon:** Hours to days
- **Examples:** "New C2 domain pattern: *.catastrophic-shield.xyz" / "APT28 using CVE-2025-66376 to exploit Zimbra"
- **Product formats:** IOC lists, detection rules (Sigma, YARA), ThreatFox/AlienVault indicators

---

## Intelligence Cycle (FIRST CTI-SIG)

1. **Direction** — Define intelligence requirements (what questions need answering?)
2. **Collection** — Gather raw data from internal/external sources
3. **Processing** — Transform raw data into usable formats (parsing, deduplication, enrichment)
4. **Analysis** — Turn information into intelligence (context, meaning, implications)
5. **Dissemination** — Deliver to right audience in right format
6. **Feedback** — Refine requirements based on utility

---

## Source Reliability & Information Reliability (FIRST CTI-SIG)

### Source Reliability Ratings (A-F)

| Rating | Description |
|--------|-------------|
| A — Completely Reliable | No doubt as to authenticity, competence, or objectivity |
| B — Usually Reliable | Minor doubts about authenticity, competence, or objectivity |
| C — Fairly Reliable | Doubts about authenticity, competence, or objectivity |
| D — Not Usually Reliable | Significant doubts about authenticity, competence, or objectivity |
| E — Unreliable | Serious doubts about authenticity, competence, or objectivity |
| F — Reliability Unknown | No basis for evaluating reliability |

### Information Credibility Levels (1-5)

| Level | Description |
|-------|-------------|
| 1 — Confirmed | Confirmed by multiple independent sources |
| 2 — Probably True | Confirmed by single source, plausibility checks pass |
| 3 — Possibly True | Source reliability unknown or variable, plausible |
| 4 — Doubtfully True | Source reliability questionable, logical inconsistencies |
| 5 — Truth Cannot Be Determined | No basis for evaluation |

### Combined Reliability Matrix
When reporting CTI, communicate BOTH source reliability AND information credibility.
Example: "Source B-2" = Usually reliable source, confirmed by multiple sources.

---

## FIRST Standards for Communicating Uncertainties in CTI Reporting

### The Problem
- Vague language leads to misinterpretation
- "May," "could," "might" have different meanings to different analysts
- Overconfidence = bad decisions. Over-uncertainty = alert fatigue

### The Standard Approach
Use calibrated probability language:

| Language | Probability Range |
|----------|-------------------|
| Almost certainly | 93%+ |
| Very likely | 77-93% |
| Likely | 55-77% |
| About as likely as not | 45-55% |
| Unlikely | 23-45% |
| Very unlikely | 7-23% |
| Almost certainly not | <7% |

### Confidence Levels

| Level | Definition |
|-------|------------|
| High Confidence | Strong evidence, multiple sources, logical, consistent. Changing assessment unlikely with new data. |
| Medium Confidence | Some evidence, single source or limited corroboration. Assessment might change with new data. |
| Low Confidence | Limited evidence, anecdotal, speculative. Assessment likely to change significantly with new data. |

### Reporting Format
Always include: "We assess [claim] with [High/Medium/Low] confidence based on [source reliability] sources."
Example: "We assess APT28 is operating a new spear-phishing campaign targeting defense contractors with HIGH confidence based on B-1 sources."

---

## Threat Modeling

### Diamond Model of Intrusion Analysis
Four core features:
1. **Adversary** — Threat actor (group, individual, nation-state)
2. **Capability** — TTPs, tools, exploits (mapped to ATT&CK)
3. **Infrastructure** — C2, staging, Dropzones (IP, domain, hostnames)
4. **Victim** — Target organization, sector, geography

Analysis moves between any two nodes to generate findings.

### Kill Chain Phases (Lockheed Martin)
1. Reconnaissance
2. Weaponization
3. Delivery
4. Exploitation
5. Installation
6. C2 (Command & Control)
7. Actions on Objectives

### ATT&CK Matrix Overview
- **Pre-ATT&CK:** Recon, resource development, initial access
- **Enterprise ATT&CK:** Persistence, privilege escalation, defense evasion, discovery, lateral movement, collection, exfiltration, command & control
- **Mobile ATT&CK:** Device access, network effects, collection
- **ICS ATT&CK:** Operational technology-specific

---

## Indicator Types

### Atomic Indicators (Cannot be broken down further)
- IP addresses
- Domain names
- File hashes (MD5, SHA1, SHA256)
- CVE IDs
- Email addresses

### Computed Indicators (Derived from artifacts)
- File paths
- Registry keys
- Mutex names
- JA3/SRI hashes (for TLS)
- HASHING

### Behavioral Indicators (Patterns)
- HTTP user-agent patterns
- DNS query patterns
- Traffic timing patterns
- PowerShell command sequences
- WMI event subscription patterns

---

## TLP (Traffic Light Protocol)

| TLP | Meaning | Distribution |
|-----|---------|--------------|
| TLP:RED | Not for disclosure, restricted to participants only | Direct participants only |
| TLP:AMBER | Limited disclosure, recipients can share with org need-to-know | Org-internal only |
| TLP:AMBER+STRICT | Same as AMBER but no org-internal sharing | Org-internal, need-to-know |
| TLP:GREEN | Community distribution, can share with peers | Sector/community |
| TLP:CLEAR | Public distribution, no restrictions | Anyone |

Always mark CTI products with TLP before sharing.

---

## STIX/TAXII Overview

### STIX (Structured Threat Information Expression)
- JSON-based language for representing cyber threat intelligence
- Objects: AttackPatterns, ThreatActors, Malware, Tools, Vulnerabilities, IOCs
- Relationships between objects (APT28 **uses** Malware, APT28 **targets** Defense)
- Allows expressive, machine-readable threat reports

### TAXII (Trusted Automated eXchange of Intelligence Information)
- Transport protocol for STIX content
- Discovery → Collection → Package
- Used for automated threat intelligence sharing

### MISP (Malware Information Sharing Platform)
- Open source threat intelligence platform
- Community-driven IOC sharing
- Format: MISP JSON (similar to STIX)

---

## CTI Collection Sources

### Open Source Intelligence (OSINT)
- Security blogs (Krebs, Sophos, Mandiant, Recorded Future)
- Threat intel feeds (AlienVault OTX, ThreatFox, Abuse.ch)
- Vendor advisories (Microsoft, CISA, FBI)
- Paste sites, dark web forums (monitoring)
- Social media (Twitter/X, LinkedIn)

### Closed Intelligence
- ISACs (Information Sharing and Analysis Centers)
- Sector-specific intel sharing groups
- Government partnerships (CISA, FBI IC3)
- Commercial threat intel vendors ( Recorded Future, DomainTools, Mandiant)
- HUMINT (when legally/ethically appropriate)

---

## Analysis Techniques

### Analysis of Competing Hypotheses (ACH)
1. Identify possible hypotheses
2. List evidence for/against each
3. Assess diagnosticity of each piece of evidence
4. Revise probabilities
5. Test sensitivity to key evidence
6. Reach conclusion

### Cone of Plausibility
Assess which scenarios are:
- Possible (could happen)
- Plausible (makes sense given context)
- Probable (most likely)
- Implied (if this is true, then...)

---

## Key CTI Roles in an Organization

### Internal CTI Team Functions
- Threat actor monitoring (APT groups relevant to sector)
- Vulnerability prioritization (CVSS + EPSS + KEV)
- IOC enrichment and false positive reduction
- Detection rule development (Sigma, YARA, Splunk, Sentinel)
- Threat briefings for security ops
- Strategic intelligence for leadership

### CTI Analyst Skills
- OSINT/closed source research
- Malware analysis (static, dynamic)
- ATT&CK framework knowledge
- OSINT investigation (people, infrastructure)
- Analytical writing (intelligence products)
- Python/SQL for automation

---

## CTI Integration Points

### With SIEM/SOAR
- IOC enrichment pipelines
- Automated alert triage
- Playbook-driven response
- Correlation rules

### With Vulnerability Management
- Patch prioritization (CVSS + EPSS + threat activity)
- Risk-based vulnerability scoring
- Exploitability intelligence

### With Incident Response
- DFIR + CTI integration
- Attribution during active incidents
- Attribution for post-incident reporting
- Lessons learned feedback loop

---

## Common CTI Failures to Avoid

1. **Alert fatigue from low-quality feeds** — Filter, deduplicate, prioritize
2. **Attribution overconfidence** — Nation-state attribution is HARD; be humble
3. **Ignoring uncertainty** — Report confidence levels, not just claims
4. **Intel without action** — CTI must drive defensive action
5. **Source evaluation skip** — Always assess reliability
6. **Keeping intel in silos** — Disseminate to those who can act
7. **Ignoring strategic intel** — Don't just focus on tactical IOCs

---

## Key References
- FIRST CTI-SIG: https://www.first.org/global/sigs/cti/
- MITRE ATT&CK: https://attack.mitre.org/
- NIST Cybersecurity Framework: https://csrc.nist.gov/publications/detail/sp/800-53/rev-5/final
- Diamond Model: https://www.researchgate.net/publication/228908885_Introducing_the_Diamond_Model
- STIX/TAXII: https://oasis-open.github.io/cti-documentation/
- TLP: https://first.org/tlp/
- EPSS: https://www.first.org/epss/
- CISA KEV: https://www.cisa.gov/known-exploited-vulnerabilities-catalog
