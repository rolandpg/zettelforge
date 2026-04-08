# ISO/IEC 27002:2022 — Attributes Framework

## Overview
Each of the 93 controls carries five attribute tags enabling filtering, sorting, and mapping to external frameworks.

---

## Attribute 1: Control Type
| Tag | Meaning |
|-----|---------|
| #Preventive | Prevents incident occurrence |
| #Detective | Detects when an incident occurs |
| #Corrective | Acts after an incident to restore security |

---

## Attribute 2: Information Security Properties (CIA Triad)
| Tag | Meaning |
|-----|---------|
| #Confidentiality | Protects information from unauthorized disclosure |
| #Integrity | Protects information from unauthorized modification |
| #Availability | Ensures information is accessible when needed |

---

## Attribute 3: Cybersecurity Concepts (ISO/IEC TS 27110 / NIST CSF mapping)
| Tag | NIST CSF Function |
|-----|-------------------|
| #Identify | Understand organizational cybersecurity risk |
| #Protect | Implement safeguards |
| #Detect | Detect cybersecurity events |
| #Respond | Take action on detected events |
| #Recover | Restore capabilities after incident |

---

## Attribute 4: Operational Capabilities
| Tag | Domain |
|-----|--------|
| #Governance | Strategic direction and oversight |
| #Asset_management | Inventory and lifecycle |
| #Information_protection | Classification, handling, DLP |
| #Human_resource_security | Personnel security lifecycle |
| #Physical_security | Physical perimeters, access, environment |
| #System_and_network_security | Infrastructure hardening |
| #Application_security | Secure development and operations |
| #Secure_configuration | Baseline config management |
| #Identity_and_access_management | IAM, PAM, authentication |
| #Threat_and_vulnerability_management | CTI, vuln scanning, patching |
| #Continuity | BCP, DR, ICT readiness |
| #Supplier_relationships_security | Third-party and supply chain |
| #Legal_and_compliance | Regulatory, contractual |
| #Information_security_event_management | Incident response lifecycle |
| #Information_security_assurance | Audit, testing, review |

---

## Attribute 5: Security Domains
| Tag | Scope |
|-----|-------|
| #Governance_and_Ecosystem | ISMS governance, risk management, ecosystem/supply chain |
| #Protection | Architecture, admin, IAM, maintenance, physical security |
| #Defence | Detection, CSIRT/incident management |
| #Resilience | Business continuity, crisis management |

---

## Usage Examples

**Filter for SOC/MDR-relevant controls:**
`#Detective + #Threat_and_vulnerability_management + #Defence`
→ 5.7 Threat intelligence, 8.7 Protection against malware, 8.8 Technical vulnerability management, 8.15 Logging, 8.16 Monitoring activities

**Filter for CMMC compliance-relevant controls:**
`#Governance + #Identify + #Protect + #Legal_and_compliance`
→ 5.1 Policies, 5.12 Classification, 5.31 Legal requirements, 6.3 Awareness training, 8.5 Secure authentication, 8.8 Vulnerability management

**Filter for cloud/DIB posture:**
`5.23 + 5.19-5.22 + 8.9 + 8.12 + 8.15`
→ Cloud services, supply chain, configuration management, DLP, logging

**Filter for incident response:**
`5.24 + 5.25 + 5.26 + 5.27 + 5.28 + 6.8`
→ Full incident management lifecycle

---

## New Controls in 2022 Edition (vs. ISO 27001:2013)

| Control | Name | Key attribute |
|---------|------|---------------|
| 5.7 | Threat intelligence | #Threat_and_vulnerability_management |
| 5.23 | Information security for use of cloud services | #Supplier_relationships_security |
| 5.30 | ICT readiness for business continuity | #Continuity |
| 8.9 | Configuration management | #Secure_configuration |
| 8.10 | Information deletion | #Information_protection |
| 8.11 | Data masking | #Information_protection |
| 8.12 | Data leakage prevention | #Information_protection |
| 8.16 | Monitoring activities | #Information_security_event_management |
| 8.23 | Web filtering | #System_and_network_security |
| 8.28 | Secure coding | #Application_security |
