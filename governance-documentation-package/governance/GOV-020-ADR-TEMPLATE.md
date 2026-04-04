---
document_id: GOV-020
title: Architecture Decision Record Template
version: 1.0.0
last_updated: 2026-04-02
owner: "[CTO/CIO Name]"
classification: Internal
rag_tags: [adr, architecture, decision, record, template, rationale, tradeoffs, documentation]
compliance_mapping: [FedRAMP-CM-3, FedRAMP-SA-8, NIST-800-171-3.4.3]
---

# Architecture Decision Record Template

## Purpose

Architecture Decision Records (ADRs) capture significant technical decisions with their context, rationale, and consequences. They prevent knowledge loss when team members change, stop the same debates from recurring, and create an audit trail of architectural evolution. ADRs are lighter than RFCs (GOV-016). An ADR documents a decision that has been made. An RFC proposes a change that needs approval before implementation. Some decisions start as RFCs and are summarized as ADRs after approval.

## When to Write an ADR

Write an ADR when the team decides to: adopt or replace a framework, library, or tool; change the database or storage technology; modify the authentication or authorization approach; alter the service communication pattern (sync to async, REST to gRPC); change the deployment strategy; adopt a new design pattern or convention; or deviate from an existing governance standard with documented justification.

If you are unsure whether a decision warrants an ADR, err on the side of writing one. A short ADR that captures context costs less than re-debating a forgotten decision.

## Storage and Naming

ADRs are stored in the repository at `docs/adr/` and numbered sequentially: `ADR-0001-use-postgresql-for-primary-storage.md`. The number never changes, even if the decision is later superseded.

## Template

```markdown
# ADR-NNNN: [Short Decision Title]

## Status

[Proposed | Accepted | Deprecated | Superseded by ADR-NNNN]

## Date

[YYYY-MM-DD of the decision]

## Decision Makers

[Names and roles of people who made or approved this decision]

## Context

What is the situation that requires a decision? What forces are at play? What constraints exist? Describe the problem or opportunity that prompted this decision. Include relevant technical context, business requirements, and any prior art or related ADRs.

## Decision

State the decision clearly and concisely. "We will use X for Y because Z." This should be a single paragraph or at most a few short paragraphs. The decision should be unambiguous enough that someone reading it for the first time knows exactly what was chosen.

## Rationale

Why was this decision made? What alternatives were considered and why were they rejected? What tradeoffs does this decision accept? Be specific about the evaluation criteria and how the chosen option performed against them. If there was debate, summarize the key arguments on each side.

## Consequences

What are the positive and negative results of this decision? Include: what becomes easier, what becomes harder, what new constraints are introduced, what technical debt is created or resolved, what skills the team needs to develop, and what follow-up work is required. Be honest about the downsides. A decision with no acknowledged downsides is a decision that has not been fully evaluated.

## References

Links to related ADRs, RFCs, external documentation, benchmark results, or other supporting material.
```

## Compliance Notes

ADRs satisfy FedRAMP CM-3 (Configuration Change Control) by documenting the rationale behind architectural changes and SA-8 (Security Engineering Principles) by ensuring that security implications of architectural decisions are explicitly considered and recorded.
