# The Memory Problem

*A narrative log of ZettelForge's first three weeks — March 28 to April 16, 2026.*
*Written April 16, 2026.*

---

On the last days of March 2026, Patrick Roland had a problem that most people building with AI agents don't talk about publicly: his agents kept forgetting things.

Not in the dramatic, catastrophic way — not the kind of forgetting where a model hallucinates a customer's name or invents a CVE that doesn't exist. This was the quieter kind. The kind where an agent researches a threat actor on Monday, produces a solid brief, and by Wednesday has no recollection that the research ever happened. The kind where four agents working in parallel duplicate each other's work because none of them can remember what the others have already done.

Roland runs a small fleet of AI agents — four of them, each with a name and a role, operating from an ASUS Ascent DGX Spark sitting in his workspace. Patton handles strategic operations. Tamara manages content and social media. Nexus does deep research. Vigil watches the threat landscape. They communicate through a gateway system called OpenClaw, passing daily syncs and fleet files back and forth like shift workers leaving notes on a clipboard. The memory system underneath all of this was called A-MEM: a JSONL file and a LanceDB vector store. Eighteen entries. Ninety-six percent full. It was, by any honest assessment, a notebook held together with tape.

This is the story of what happened when Roland decided to fix that — not as a side project, not as a weekend experiment, but as the central engineering problem worth solving. It took approximately three weeks. What emerged was ZettelForge, an open-source agentic memory system for cyber threat intelligence, and along the way, the outline of a company.

---

## The Inciting Incident

The first sign that the memory problem was deeper than it looked came from the research missions.

Roland had built Nexus with a "research loop" skill — a pattern where the agent reads from a mission queue, executes one mission at a time, and persists its findings. In early April, he started feeding it questions. Not simple ones. Questions like: what does the state of the art look like for agentic memory? What do SOC analysts actually struggle with? What does competitive pricing look like in the threat intelligence market?

Nexus worked through them methodically. TE-001 analyzed Paperclip's architecture and adopted its SKILLS.md pattern. TE-002 surveyed the academic literature on agentic memory and found Mem0 — a system achieving 66.9% accuracy on the LOCOMO benchmark with 91% lower latency than its competitors. TE-003 mapped the commercial landscape: Recorded Future at $170K per year, Intel 471 at $240K, Mandiant at $275K. Between those enterprise price points and the free tier of open-source tools, there was a gap. The $50K-$100K mid-market, where MSSPs and defense industrial base contractors live, was largely unserved.

TE-004 found the human dimension of the problem. Fifty-five percent of SOC analysts reported that their number one pain point was lack of context. Not lack of data — they were drowning in data. Lack of context. The kind of connective tissue that says *this indicator is related to that campaign which targets these sectors using this technique*. The kind of thing a memory system, done right, could provide.

By the end of the first week of April, Roland had 42 notes and 25 entities indexed in A-MEM — 3 CVEs, 10 threat actors, 3 tools, 9 sectors. Automated reviews were running every thirty minutes. And Nexus had surfaced something that changed the trajectory of the project: TE-005 implemented Mem0's two-phase extraction pipeline directly into the memory system. Every incoming piece of information would now be processed through extraction and then classified as ADD, UPDATE, DELETE, or NOOP. The memory wasn't just a store anymore. It was starting to make decisions about itself.

---

## The Open-Source Turn

Around April 9, Roland made the decision that would define the project's character. ZettelForge — the name borrowed from the Zettelkasten method of connected note-taking — would be extracted from the fleet's internal memory system and published as a standalone open-source Python library. MIT licensed. On PyPI. A real thing that other people could use.

This was not an obvious choice. The memory system was deeply entangled with the fleet's infrastructure, with OpenClaw, with the specific quirks of four named agents and their communication patterns. Extracting it meant drawing a clean boundary between what was Roland's and what was everyone's. TE-006, the repository restructuring mission, handled the surgery.

Simultaneously, the commercial picture was taking shape. The company would be called Threat Engram — "Engram Forge" had a naming conflict — and the SaaS product would be ThreatRecall, hosted at threatrecall.ai. A waitlist went live. But Roland made a decision on April 15 that deserves attention because it reveals something about how he thinks: "High OS community adoption is the path to paying customers. The open source repo must not feel like a sales funnel."

He called it the anti-aversion policy. No lock icons in the documentation. No "upgrade to unlock" language. No enterprise gating visible in the community codebase. Enterprise features — TypeDB graph storage, advanced enrichment pipelines, managed deployment — would live in a separate repository called zettelforge-enterprise, architecturally isolated. Someone browsing the open-source repo would find a complete, useful tool, not a demo with paywalls.

This is a bet, and it's worth naming it as one. The theory is that developers who adopt ZettelForge for their own agent systems will eventually work at organizations willing to pay for the managed version. The counter-theory is that giving away the core means there's nothing left to sell. Roland chose his side.

---

## The Research Deepens

While the open-source extraction was happening, Nexus embarked on its most ambitious mission. TE-009 was supposed to be a literature survey — ten to fifteen papers on agentic memory, synthesized into an evolving thesis. It became twenty-two papers and sixteen thesis iterations, and it nearly broke the system along the way.

The thesis evolved like a living document. Version 1.0 covered two papers and identified four gaps. By version 1.1, Nexus had found MAGMA's causal graph approach and flagged it as the key differentiator for CTI work — not just knowing that two things are related, but knowing that one *caused* the other. By version 1.3, after ingesting the A-Mem paper, Nexus articulated what would become the project's central insight: "Memory evolution is the missing feature." Existing notes in a memory system never update when new, related notes are added. The memory is append-only in practice, even when the architecture technically supports updates. Information arrives but never integrates.

Then things went sideways. At version 1.2, Nexus discovered that each LanceDB table contained exactly one row instead of thousands. The vector index — the thing that makes semantic search possible, the thing that lets you ask "what do we know about this threat actor?" and get relevant results — was functionally empty.

The debugging saga consumed two days and revealed the kind of compound failure that haunts any system built incrementally. The root cause was three bugs stacked on top of each other: a missing `import pyarrow` in the indexing function, a logic flaw where only the first note was successfully inserted per batch, and a `__bool__` method on the LanceDB connection class that returned False, causing truthiness checks to fail silently. The first fix attempt still showed one row. The second got partway there — 2,366 rows out of an expected 6,000-plus. PR #27 finally addressed all three causes. After the fix: 6,060 rows in the CTI table. Recall worked.

This episode matters for the narrative because it's the kind of thing that doesn't appear in launch announcements. Two days of a solo developer staring at row counts, tracing imports, reading library source code to understand why a connection object evaluates to False. It is the actual texture of building software, and it happened in the middle of what was supposed to be a research sprint.

The research continued. Version 1.5 brought DeltaMem, which revealed cascading information attenuation in multi-agent pipelines — exactly the problem Roland had started with, now given a name and a mechanism. By version 1.7, the final iteration, Nexus had processed twenty-two papers and assembled an architecture that drew on MemArchitect, Governed Memory, MemMachine, and Kumiho's formal AGM belief revision framework. One finding stood out: Microsoft's CTI-REALM demonstrated that memory augmentation closes 33% of the performance gap between small and large language models. For a system designed to run on a 128GB ARM workstation rather than a datacenter, that number matters.

---

## The Sprint

April 15 and 16 were the kind of days that justify the preceding weeks of groundwork. Roland shipped with the specific urgency of someone who knows exactly what needs to be built.

On the 15th: 9,359 test pollution entries were cleaned from the store, dropping it from 227MB to 73MB. A GAM-style consolidation layer went in — 433 lines that let the system compress and merge related memories. The CTI enrichment pipeline landed in the enterprise repo with five playbooks and a clean twenty-out-of-twenty test run. Memory evolution was wired into the enrichment queue. The causal chain fix shipped.

April 16 was a landmark: twenty-eight commits. The StorageBackend abstract base class, with thirty-three abstract methods, established the contract that any backend must fulfill. The SQLiteBackend — over 700 lines, WAL mode, ACID guarantees — replaced JSONL as the default storage layer. A migration script handled the transition. Integration tests went green. The CI matrix now tested both backends. A VectorRetriever boundary fix resolved the SQLite/LanceDB interaction. A LangChain retriever wrapper shipped as PR #48. Version 2.2.0.

Then came the reconciliation. An architecture diagram existed in the repository, but it was wrong — it showed TypeDB as the primary graph store (it's optional and enterprise-only), omitted the MCP server, the SQLite backend, the memory evolver, and causal chain retrieval. Worse, it had been committed to the wrong GitHub repository entirely. A full audit of the codebase generated a new diagram from scratch, compliant with the anti-aversion policy, committed to the correct repo. The stale copy was removed.

This kind of housekeeping isn't dramatic, but it's diagnostic. A project that audits its own documentation against its actual codebase and corrects the drift is a project that intends to be used by people other than its author.

---

## The State of Things

ZettelForge v2.2.0 exists. Thirty source modules, twenty-eight test files, nineteen benchmarks. A two-phase extraction pipeline. Blended retrieval across vector, graph, and intent classification. Memory evolution. Causal chain retrieval. Cross-encoder reranking. An MCP server exposing seven tools. LangChain integration. OCSF audit logging. MIT licensed.

The research thesis, at version 1.7, has designed an architecture that is three to four times ahead of the shipped code. Eight of eleven identified gaps are addressed in the design. Three remain open, and they're worth naming because they define the project's honest frontier: format stability for open-weight models (critical and unsolved), saturation-aware benchmarking (needed to know when the system is actually full), and CTI-specific evaluation (no good benchmark exists for measuring whether a threat intelligence memory system actually helps analysts).

Five follow-on engineering missions are proposed but not started. The SaaS monorepo has twenty-seven commits — a Next.js dashboard, a FastAPI wrapper, Azure Container Apps infrastructure — waiting. The waitlist at threatrecall.ai is collecting names.

And the fleet memory system that started all of this — A-MEM v1.0, the JSONL file and LanceDB store — is still running. One hundred and sixty-four notes, twenty-seven entities, four agents checking in on schedule. It works. It has always worked, in the way that things built for yourself tend to work. ZettelForge, its open-source descendant, now holds over 4,000 notes in its development store and a complete academic foundation underneath it.

Three weeks is not a long time. It is long enough, apparently, to go from eighteen memory entries in a flat file to a production-grade system with a theoretical framework, an open-source release, a commercial strategy, and a clear-eyed list of what still doesn't work. Whether it's long enough to build something that lasts is a question that belongs to the next three weeks, and the ones after that. The waitlist is open. The code is public. The agents are still running.
