---
document_id: GOV-016
title: RFC / Design Document Template
version: 1.0.0
last_updated: 2026-04-02
owner: "[CTO/CIO Name]"
classification: Internal
rag_tags: [rfc, design-document, proposal, architecture, review, template, decision-making]
compliance_mapping: [FedRAMP-SA-8, FedRAMP-CM-3, NIST-800-171-3.4.3]
---

# RFC / Design Document Template

## Purpose

This document provides the standard template for proposing significant technical changes. Any change that meets the threshold defined in GOV-001 (more than 2 days of effort, or any change touching authentication, authorization, data models, or external APIs) requires a design document before implementation begins. The design document ensures that technical decisions are deliberate, reviewed, and documented.

## Process

The author writes the RFC using this template and submits it as a pull request to the project repository in the `docs/rfcs/` directory. The file is named `RFC-NNN-short-title.md` where NNN is the next sequential number. Reviewers are assigned based on the affected domains. Discussion happens in PR comments. Once approved, the RFC is merged and its status is updated to "Accepted." Implementation may begin after acceptance.

## Template

```markdown
# RFC-NNN: [Title]

## Metadata

- **Author**: [Name]
- **Status**: Draft | In Review | Accepted | Rejected | Superseded
- **Created**: [Date]
- **Last Updated**: [Date]
- **Reviewers**: [Names/Roles]
- **Related Tickets**: [PROJ-XXX]
- **Related RFCs**: [RFC-NNN if applicable]

## Summary

One paragraph describing the proposed change and its purpose. A reader should understand the scope and intent after reading only this section.

## Motivation

What problem does this solve? Why is the current state insufficient? Include specific pain points, metrics, or incidents that motivate the change. Reference business requirements or user stories where applicable.

## Proposed Design

Detailed description of the proposed solution. Include:

### Architecture Changes

How the system architecture changes. Include before/after diagrams if the topology changes. Reference affected components from the Component Registry (GOV-005 COMPONENTS.md) by name and file path.

### Data Model Changes

New or modified database schemas, entities, relationships, and migrations. Specify field names, types, constraints, and indexes. Describe the migration strategy for existing data.

### API Changes

New or modified endpoints per the API Design Standards (GOV-005). Include request/response schemas. Specify backward compatibility implications. If this is a breaking change, describe the versioning and migration plan.

### Security Considerations

Threat assessment per GOV-011. How does this change affect the attack surface? What new threats does it introduce and how are they mitigated? Does this change require security reviewer approval?

### Observability

What new logging, metrics, or tracing is needed per GOV-012? What alerts should be configured? How will operators know this feature is working correctly?

## Alternatives Considered

Describe at least two alternative approaches that were evaluated and explain why they were not selected. This section demonstrates that the proposal is a deliberate choice rather than the first idea that came to mind.

## Implementation Plan

High-level sequence of implementation steps. Reference the Implementation Plan format from the Software Documentation Agent if this is a large effort. Include estimated effort per step.

## Rollout Strategy

How will this change be deployed? Feature flag? Gradual rollout? Big-bang migration? What is the rollback plan if the change causes problems?

## Open Questions

List any unresolved questions that need input from reviewers or stakeholders before implementation can proceed.

## Decision

[Filled in after review]

**Decision**: Accepted / Rejected / Deferred
**Date**: [Date]
**Decision Maker**: [Name/Role]
**Rationale**: [Brief explanation of why the decision was made]
```

## Compliance Notes

The RFC process satisfies FedRAMP CM-3 (Configuration Change Control) by documenting significant changes before implementation, and SA-8 (Security Engineering Principles) by requiring security considerations in every design proposal. RFCs, once merged, serve as permanent audit evidence of architectural decisions.
