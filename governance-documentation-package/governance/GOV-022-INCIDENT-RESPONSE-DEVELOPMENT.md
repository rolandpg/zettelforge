---
document_id: GOV-022
title: Development Incident Response Procedures
version: 1.0.0
last_updated: 2026-04-02
owner: "[CTO/CIO Name]"
classification: Internal
rag_tags: [incident-response, security-incident, outage, severity, escalation, retrospective, postmortem, on-call, runbook]
compliance_mapping: [FedRAMP-IR-1, FedRAMP-IR-4, FedRAMP-IR-5, FedRAMP-IR-6, FedRAMP-IR-8, NIST-800-171-3.6.1, NIST-800-171-3.6.2]
---

# Development Incident Response Procedures

## Purpose

This document defines how the engineering team responds to security incidents, service outages, and other operational events that originate from or affect software systems. This is not a replacement for the organization's broader incident response plan. It is the engineering-specific complement that covers: how developers are notified and engaged, how code-level issues are diagnosed and fixed, how emergency changes are deployed, and how post-incident retrospectives drive improvement.

## Incident Classification

### Severity 1 (Critical)

Complete service outage affecting all users, confirmed data breach or data loss, active exploitation of a vulnerability in production, or compromise of authentication/authorization systems. Response time: immediate (within 15 minutes of detection). All hands on deck. CTO/CIO is notified immediately.

### Severity 2 (High)

Partial service degradation affecting a significant subset of users, confirmed vulnerability with a known exploit but no evidence of active exploitation, secrets exposure (credential leak in logs, accidental commit to public repo), or data integrity issues affecting production data. Response time: within 1 hour. On-call engineer and CTO/CIO are engaged.

### Severity 3 (Medium)

Minor service degradation with workaround available, vulnerability identified by scanning tools with no known exploit, non-critical system failures (monitoring gaps, CI pipeline failures affecting deployment), or elevated error rates not yet affecting user experience. Response time: within 4 business hours. On-call engineer is engaged.

### Severity 4 (Low)

Cosmetic issues, non-security bugs affecting edge cases, performance degradation within acceptable SLO boundaries, or infrastructure drift detected but not yet impactful. Response time: next business day. Tracked in the issue backlog.

## Detection and Notification

Incidents are detected through three channels: automated monitoring and alerting (GOV-012) which sends alerts to the on-call channel, external reports (customer-reported issues, vulnerability disclosures), and internal discovery (developer notices an issue during normal work).

When an incident is detected, the discoverer creates an incident ticket with the severity classification, a brief description of symptoms, the time of detection, and the affected systems. For Severity 1 and 2, the discoverer also sends a notification to the designated incident channel immediately, without waiting for a complete diagnosis.

## Response Process

### Step 1: Triage

The on-call engineer (or CTO/CIO for Severity 1) confirms the severity classification, identifies the affected systems and blast radius, and determines whether the incident is ongoing or has already resolved.

### Step 2: Containment

For security incidents: isolate affected systems, rotate compromised credentials (GOV-014 emergency rotation), block attack vectors if identified. For outages: determine if the issue can be resolved by rolling back to the previous deployment (GOV-010 rollback procedure). If rollback resolves the issue, proceed to Step 4.

### Step 3: Remediation

For issues requiring a code fix: follow the emergency change process in GOV-001. Create a hotfix branch, implement the minimal fix, perform synchronous paired review, deploy through the CI/CD pipeline (expedited but not bypassed). For configuration issues: apply the fix through the infrastructure-as-code process, review the change with a peer, and deploy.

### Step 4: Recovery Verification

Verify that the fix resolves the incident. Monitor error rates, latency, and affected metrics for 30 minutes post-fix. Confirm with affected users or systems that normal operation has resumed. Update the incident ticket with the resolution.

### Step 5: Communication

For Severity 1 and 2 incidents: send a resolution notification to all stakeholders with a brief summary of what happened, what was done, and when normal operation resumed. For incidents affecting external users or clients: coordinate communication with the appropriate business stakeholders before sending external notifications.

## Post-Incident Retrospective

Every Severity 1 and 2 incident, and any Severity 3 incident with interesting lessons, receives a post-incident retrospective within 5 business days of resolution. The retrospective is a blameless review that documents:

What happened (timeline of events from detection through resolution). Why it happened (root cause analysis, not "who made the mistake" but "what system failure allowed this to occur"). How it was detected (was it monitoring, a customer report, or accidental discovery?). How it was resolved (what actions were taken). What will prevent recurrence (specific action items with owners and deadlines).

Action items from retrospectives are tracked as tickets in the project backlog. Security-related action items are prioritized per the security debt category in GOV-015.

Retrospectives are stored in the repository at `docs/incidents/` and named `INC-NNNN-short-description.md`.

## Secrets Exposure Response

If a secret (credential, API key, token, certificate private key) is exposed in any channel (committed to version control, logged, sent in clear text, shared in a message), the following procedure is mandatory:

Immediately rotate the exposed secret per GOV-014 emergency rotation. Invalidate all sessions or tokens derived from the exposed secret. Determine the exposure window (how long was the secret exposed, who or what could have accessed it). Search logs for unauthorized use of the exposed secret during the exposure window. If unauthorized use is detected, escalate to Severity 1. Document the incident and conduct a retrospective to prevent recurrence.

If the secret was committed to version control, rotating it is not sufficient. The commit history contains the secret permanently. If the repository is or was ever public, assume the secret is compromised regardless of how quickly it was removed from the current branch. If the repository is private, assess the risk based on who has access.

## Compliance Notes

This document supports FedRAMP IR-1 (Incident Response Policy and Procedures), IR-4 (Incident Handling), IR-5 (Incident Monitoring), IR-6 (Incident Reporting), and IR-8 (Incident Response Plan). Incident tickets, retrospective documents, and communication records serve as audit evidence. The engineering incident response procedures integrate with the organization's broader incident response plan and do not replace it.
