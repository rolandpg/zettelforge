# ISO/IEC 27002:2022 — Organizational Controls (5.1–5.37)

**37 controls | Theme: Organizational**

---

## 5.1 Policies for Information Security
**Attributes:** #Preventive | #CIA | #Identify | #Governance | #Governance_and_Ecosystem #Resilience

**Control:** Information security policy and topic-specific policies should be defined, approved by management, published, communicated and acknowledged by relevant personnel and interested parties, and reviewed at planned intervals or when significant changes occur.

**Purpose:** Ensure continuing suitability, adequacy, effectiveness of management direction and support for IS.

**Key Points:**
- High-level IS policy approved by top management covering: definition of IS; objectives; principles; commitment; assignment of responsibilities; exemption procedures
- Topic-specific policies on: access control; physical/environmental security; asset management; information transfer; secure config of user endpoints; network security; IS incident management; backup; cryptography/key management; classification and handling; technical vulnerability management; secure development
- Review triggers: business strategy changes; technical environment; regulations; IS risks; threat environment; lessons learned

---

## 5.2 Information Security Roles and Responsibilities
**Attributes:** #Preventive | #CIA | #Identify | #Governance | #Governance_and_Ecosystem #Protection #Resilience

**Purpose:** Establish defined, approved, and understood structure for IS implementation, operation, and management.

**Key Points:**
- Define responsibilities for: protection of assets; specific IS processes; risk management; all users of information and assets
- Each security area must have a designated responsible individual
- Delegation of tasks allowed but accountability remains
- Define competence requirements per role
- Common practice: appoint IS manager; appoint asset owner per asset

---

## 5.3 Segregation of Duties
**Attributes:** #Preventive | #CIA | #Protect | #Governance #Identity_and_access_management | #Governance_and_Ecosystem

**Purpose:** Reduce risk of fraud, error, and bypassing of IS controls.

**Key Points:**
- Separate conflicting duties between different individuals
- Activities requiring segregation: initiating/approving changes; requesting/approving/implementing access rights; designing/implementing/reviewing code; developing software and administering production; using and administering applications; using applications and administering databases
- Consider collusion risk in design
- Small orgs: apply as far as practicable; supplement with monitoring, audit trails, supervision
- RBAC: use automated tools to identify conflicting roles

---

## 5.4 Management Responsibilities
**Attributes:** #Preventive | #CIA | #Identify | #Governance | #Governance_and_Ecosystem

**Purpose:** Ensure management understands their IS role and that personnel fulfil IS responsibilities.

**Key Points:** Management must ensure personnel:
- Are briefed on IS roles before access granted
- Have guidelines stating IS expectations
- Are mandated to fulfil IS policy
- Achieve appropriate IS awareness level
- Comply with employment terms re: IS
- Maintain skills through ongoing education
- Have a confidential reporting channel (whistleblowing)
- Have adequate resources for IS processes

---

## 5.5 Contact with Authorities
**Attributes:** #Preventive #Corrective | #CIA | #Identify #Protect #Respond #Recover | #Governance | #Defence #Resilience

**Purpose:** Ensure appropriate information flow between organization and legal, regulatory, supervisory authorities.

**Key Points:**
- Define when and by whom authorities are contacted (law enforcement, regulators, supervisors)
- Define how IS incidents are reported in timely manner
- Contacts can request action against attack sources
- Use contacts for: incident management; contingency planning; business continuity
- Other authorities: utilities, emergency services, ISPs, water suppliers

---

## 5.6 Contact with Special Interest Groups
**Attributes:** #Preventive #Corrective | #CIA | #Protect #Respond #Recover | #Governance | #Defence

**Purpose:** Ensure appropriate IS information flow.

**Key Points:** Membership provides:
- Best practices and staying current
- Early warnings on attacks/vulnerabilities/patches
- Specialist IS advice
- Information sharing on new technologies/threats/vulnerabilities
- Liaison points for IS incidents

---

## 5.7 Threat Intelligence ⭐ NEW IN 2022
**Attributes:** #Preventive #Detective #Corrective | #CIA | #Identify #Detect #Respond | #Threat_and_vulnerability_management | #Defence #Resilience

**Purpose:** Provide awareness of organization's threat environment to enable appropriate mitigation.

**Three Layers:**
- **Strategic:** High-level info on changing threat landscape (types of attackers/attacks)
- **Tactical:** Attacker methodologies, tools, technologies
- **Operational:** Specific attack details including technical indicators

**Quality Criteria:** Relevant, insightful, contextual, actionable

**Process:**
1. Establish objectives for threat intelligence production
2. Identify, vet, and select internal and external information sources
3. Collect information from sources
4. Process for analysis (translate, format, corroborate)
5. Analyse for relevance to organization
6. Communicate and share to relevant individuals

**Uses:**
- Input to risk management processes
- Additional input to technical preventive/detective controls (firewalls, IDS, anti-malware)
- Input to IS test processes
- Share with other organizations on mutual basis

---

## 5.8 Information Security in Project Management
**Attributes:** #Preventive | #CIA | #Identify #Protect | #Governance | #Governance_and_Ecosystem #Protection

**Purpose:** Ensure IS risks related to projects are effectively addressed throughout the project lifecycle.

**Key Points:** Project management must require:
- IS risks assessed and treated early and periodically
- IS requirements addressed in early project stages
- IS risks associated with execution considered throughout
- Progress on risk treatment reviewed, effectiveness evaluated and tested

**IS requirements should consider:** information involved and classification; CIA protection needs; authentication assurance; access provisioning; user duties; business process requirements (logging, non-repudiation); legal/regulatory environment

---

## 5.9 Inventory of Information and Other Associated Assets
**Attributes:** #Preventive | #CIA | #Identify | #Asset_management | #Governance_and_Ecosystem #Protection

**Purpose:** Identify assets to preserve IS and assign appropriate ownership.

**Key Points:**
- Identify, document importance in dedicated or existing inventories
- Keep accurate, up-to-date, consistent
- Include asset location where appropriate
- Can be dynamic inventories (hardware, software, VMs, facilities, personnel, competence, records)
- Each asset classified per information classification scheme

**Ownership:**
- Assign owner (individual or group) for each asset
- Process for timely assignment on creation or transfer
- Owner duties: ensure inventoried, classified, protected; review classification; list supporting tech; define acceptable use requirements; ensure access restrictions correspond with classification; handle deletion/disposal securely; be involved in risk management

---

## 5.10 Acceptable Use of Information and Other Associated Assets
**Attributes:** #Preventive | #CIA | #Protect | #Asset_management #Information_protection | #Governance_and_Ecosystem #Protection

**Purpose:** Ensure assets are appropriately protected, used, and handled.

**Key Points:**
- Topic-specific policy should state: expected/unacceptable behaviours; permitted/prohibited use; monitoring activities
- Procedures cover full information lifecycle
- Consider: access restrictions per classification; authorized user records; protection of copies; storage per manufacturer specs; authorization of disposal/deletion methods
- Where assets not directly owned (public cloud): identify applicable use controls through agreements

---

## 5.11 Return of Assets
**Attributes:** #Preventive | #CIA | #Protect | #Asset_management | #Protection

**Purpose:** Protect organization's assets during employment change or termination.

**Key Points:**
- Formalize change/termination process to include return of all physical and electronic assets
- Where personnel use own equipment: ensure relevant information is traced, transferred, and securely deleted
- Knowledge transfer for operationally critical personnel
- During notice period: prevent unauthorized copying
- Assets: user endpoint devices; portable storage; specialist equipment; auth hardware (keys, tokens, smartcards); physical copies of information

---

## 5.12 Classification of Information
**Attributes:** #Preventive | #CIA | #Identify | #Information_protection | #Protection #Defence

**Purpose:** Ensure identification and understanding of protection needs aligned with importance to organization.

**Key Points:**
- Establish topic-specific policy on information classification
- Consider: CIA requirements; business needs for sharing/restricting; legal requirements
- Owners accountable for their classification
- Scheme must include conventions and criteria for periodic review
- Align with access control policy
- Scheme must be consistent across the whole organization

**Example 4-level confidentiality scheme:**
- Level 1: Disclosure causes no harm
- Level 2: Minor reputational damage or minor operational impact
- Level 3: Significant short-term impact on operations or business objectives
- Level 4: Serious impact on long-term business objectives or survival

---

## 5.13 Labelling of Information
**Attributes:** #Preventive | #CIA | #Protect | #Information_protection | #Defence #Protection

**Purpose:** Facilitate communication of classification and support automation of information processing/management.

**Labelling Techniques:** Physical labels; headers and footers; metadata; watermarking; rubber-stamps

**Key Points:**
- Procedures cover all formats
- Labels must be easily recognizable
- Digital information should utilize metadata for identification, management, control
- Metadata should enable efficient searching and automated decision-making based on classification
- Output from systems containing sensitive/critical information must carry appropriate label

---

## 5.14 Information Transfer
**Attributes:** #Preventive | #CIA | #Protect | #Asset_management #Information_protection | #Protection

**Purpose:** Maintain security of information transferred within organization and to external parties.

**Key Points (all transfer types):**
- Controls against: interception, unauthorized access, copying, modification, misrouting, destruction, DoS
- Controls for traceability and non-repudiation; chain of custody
- Identification of appropriate contacts
- Responsibilities and liabilities for incidents
- Agreed labelling system for sensitive/critical information
- Reliability and availability of transfer service
- Acceptable use guidelines
- Retention and disposal guidelines

**Electronic transfer additionally:** detection/protection against malware; approval/authorization procedures; legal requirements for information (digital signatures, encryption); incident handling; agreed encryption standards

---

## 5.15 Access Control
**Attributes:** #Preventive | #CIA | #Protect | #Identity_and_access_management | #Protection

**Purpose:** Ensure authorized access and prevent unauthorized access to information and associated assets.

**Key Points:**
- Topic-specific policy defining: what entities require what access; application security; physical access; classification; privileged access restrictions; SoD; legislation; authorization processes; access rights management; logging
- Common principles: need-to-know, need-to-use
- "Everything is generally forbidden unless expressly permitted" (least privilege default)
- Implementation methods: MAC (Mandatory), DAC (Discretionary), RBAC (Role-Based), ABAC (Attribute-Based)

---

## 5.16 Identity Management
**Attributes:** #Preventive | #CIA | #Protect | #Identity_and_access_management | #Protection

**Purpose:** Allow unique identification of individuals and systems; enable appropriate access rights assignment.

**Key Points:**
- Single identity linked to single person to maintain accountability
- Shared identities: only where necessary, require dedicated approval and documentation
- Non-human entity identities: require appropriately segregated approval and independent ongoing oversight
- Disable/remove identities promptly when no longer required
- Avoid duplicate identities
- Maintain records of significant events re: identity use and management
- Third-party provided identities (e.g., social media): ensure required trust level; manage associated risks

---

## 5.17 Authentication Information
**Attributes:** #Preventive | #CIA | #Protect | #Identity_and_access_management | #Protection

**Purpose:** Ensure proper entity authentication and prevent authentication failures.

**Allocation:**
- Auto-generated passwords during enrollment: non-guessable, unique, changed after first use
- Verify user identity before providing new/replacement/temporary auth information
- Transmit auth information securely (no clear text)
- Change default vendor-supplied credentials immediately after installation

**User Responsibilities:**
- Keep passwords confidential and do not share
- Change compromised credentials immediately
- Select strong passwords: passphrases; alphanumeric + special chars; minimum length; not based on personal info or dictionary words
- Do not reuse passwords across services

**Password Management System:**
- Allow user selection and change with confirmation
- Enforce strong passwords
- Force change at first login and after security incidents
- Prevent reuse of previous passwords
- Block commonly-used and compromised passwords
- Never display passwords on screen
- Store and transmit in protected form

---

## 5.18 Access Rights
**Attributes:** #Preventive | #CIA | #Protect | #Identity_and_access_management | #Protection

**Purpose:** Ensure access to information and assets is defined and authorized per business requirements.

**Provision/Revocation:**
- Obtain authorization from information/asset owner
- Consider SoD (separate approval from implementation roles)
- Remove access when no longer needed, especially on departure
- Consider temporary access with defined expiry dates
- Verify access level is consistent with policies and SoD
- Activate only after authorization complete
- Maintain central record of access rights granted
- Modify on role/job changes

**Review:**
- Regularly review after organizational changes or employment termination
- Review privileged access rights authorizations

**Pre-Termination:**
- Review and adjust/remove access based on: reason for termination; current responsibilities; value of accessible assets

---

## 5.19 Information Security in Supplier Relationships
**Attributes:** #Preventive | #CIA | #Identify #Protect #Detect #Respond | #Supplier_relationships_security | #Governance_and_Ecosystem

**Purpose:** Maintain agreed level of IS in supplier relationships.

**Key Points:**
- Establish and communicate topic-specific policy on supplier relationships
- Identify types of suppliers that can affect CIA
- Processes for evaluating and selecting suppliers per sensitivity
- Assess suppliers' products/services for adequate IS controls
- Define what info, ICT services, physical infrastructure suppliers can access/monitor/control
- Assess IS risks associated with suppliers' use of organizational information
- Handle incidents and contingencies associated with supplier products/services
- Manage knowledge transfer and transitions securely
- Define requirements for secure termination: de-provision access; information handling; IP ownership; portability; records; asset return; secure disposal; ongoing confidentiality

---

## 5.20 Addressing Information Security Within Supplier Agreements
**Attributes:** #Preventive | #CIA | #Protect | #Supplier_relationships_security | #Governance_and_Ecosystem

**Purpose:** Maintain agreed level of IS in supplier relationships.

**Agreement should address:**
- Description of information to be provided/accessed and methods
- Information classification per organizational scheme with mapping between schemes
- Legal, statutory, regulatory, contractual requirements (PII, IP)
- Obligations for both parties for controls including access control, monitoring, reporting, auditing
- Acceptable use rules
- Authorization procedures for supplier personnel access
- Minimum IS requirements for supplier ICT infrastructure
- Indemnities and remediation for failure
- Incident management requirements and procedures
- Training and awareness requirements
- Sub-contracting provisions
- Screening requirements for supplier personnel
- Right to audit supplier processes and controls
- Defect and conflict resolution
- Backup provisions
- DR site availability
- Change management with advance notification
- Physical security controls commensurate with classification
- Termination clauses: records management; asset return; secure disposal; ongoing confidentiality
- Maintain register of agreements; regularly review and update

---

## 5.21 Managing Information Security in the ICT Supply Chain
**Attributes:** #Preventive | #CIA | #Identify #Protect | #Supplier_relationships_security | #Governance_and_Ecosystem

**Purpose:** Maintain agreed level of IS in supplier relationships.

**Key Points:**
- Define IS requirements for ICT product/service acquisition
- Require ICT service suppliers to propagate security requirements through their sub-contracted supply chain
- Require software suppliers to provide software bill of materials (SBOM)
- Request information describing implemented security functions and configuration
- Implement monitoring/validation that delivered ICT products comply with stated requirements (pen testing, third-party attestations)
- Identify and document critical components requiring increased scrutiny
- Obtain assurance that critical components can be traced throughout supply chain
- Obtain assurance that delivered ICT products function as expected without unexpected features
- Implement anti-tamper processes (anti-tamper labels, cryptographic hash verifications, digital signatures)
- Consider formal certification (Common Criteria)
- Define rules for sharing supply chain issues
- Manage ICT component lifecycle and availability risks

---

## 5.22 Monitoring, Review and Change Management of Supplier Services
**Attributes:** #Preventive #Detective #Corrective | #CIA | #Identify #Detect #Respond | #Supplier_relationships_security | #Governance_and_Ecosystem

**Purpose:** Maintain agreed level of IS and service delivery per supplier agreements.

**Key Points:**
- Monitor performance levels for compliance with agreements
- Monitor supplier changes: enhancements; new applications/systems; policy/procedure modifications; new/changed controls
- Monitor service changes: network changes; new technologies; version adoptions; new dev tools; physical location changes; sub-supplier changes
- Review service reports; hold regular progress meetings
- Conduct audits of suppliers and sub-suppliers
- Review and manage IS incidents
- Review supplier audit trails and records
- Identify and manage IS vulnerabilities
- Review supplier's own supplier relationships
- Assign designated individual/team for managing supplier relationships

---

## 5.23 Information Security for Use of Cloud Services ⭐ NEW IN 2022
**Attributes:** #Preventive #Detective #Corrective | #CIA | #Identify #Protect #Detect #Respond #Recover | #Supplier_relationships_security | #Governance_and_Ecosystem

**Purpose:** Specify and manage IS for the use of cloud services.

**Organization should define:**
- IS requirements for cloud services used
- Cloud service selection criteria and scope
- Roles and responsibilities for use and management
- Which controls are managed by cloud provider vs. organization
- How to obtain and utilize cloud provider security capabilities
- How to obtain assurance on cloud provider controls
- How to manage controls when using multiple cloud services
- Procedures for handling security incidents in cloud environments
- Approach for monitoring, reviewing, and evaluating ongoing cloud use
- Cloud exit strategy

**Cloud service agreements should include:**
- Industry-accepted architecture/infrastructure standards
- Access controls meeting organizational requirements
- Malware monitoring and protection
- Processing/storing sensitive information only in approved locations/jurisdictions
- Dedicated incident response support
- Security requirements met even if sub-contracted
- Support for digital evidence gathering across jurisdictions
- Support and availability when organization wants to exit
- Required backup of data and configuration
- Return of config files, source code, and data owned by organization

---

## 5.24 Information Security Incident Management Planning and Preparation
**Attributes:** #Corrective | #CIA | #Respond #Recover | #Information_security_event_management | #Defence

**Purpose:** Ensure quick, effective, consistent, and orderly response to IS incidents.

**Key Points:**
- Common method for reporting IS events with defined point of contact
- Incident management process: administration, documentation, detection, triage, prioritization, analysis, communication, coordination
- Incident response process: assessing, responding, learning
- Only competent, trained personnel handle IS incidents
- Process for identifying training, certification, ongoing development requirements

**Procedures should cover:**
- Evaluation of events against incident criteria
- Monitoring, detecting, classifying, analyzing, reporting
- Managing incidents to conclusion including escalation
- Coordination with internal and external parties
- Logging incident management activities
- Handling evidence
- Root cause analysis
- Lessons learned identification

**Reporting should include:**
- Actions to take when an IS event occurs
- Incident forms for reporting support
- Feedback processes to notify reporters of outcomes
- Consideration of external requirements for breach notification to regulators within defined time frames

---

## 5.25 Assessment and Decision on Information Security Events
**Attributes:** #Detective | #CIA | #Detect | #Information_security_event_management | #Defence

**Purpose:** Ensure effective categorization and prioritization of IS events.

**Key Points:**
- Agree on categorization and prioritization scheme for IS incidents
- Scheme should include criteria to categorize events as IS incidents
- Point of contact should assess each event using agreed scheme
- Record results of assessments and decisions in detail for future reference

---

## 5.26 Response to Information Security Incidents
**Attributes:** #Corrective | #CIA | #Respond | #Information_security_event_management | #Defence

**Purpose:** Ensure efficient and effective response to IS incidents.

**Response should include:**
- Containing affected systems if consequences can spread
- Collecting evidence as soon as possible
- Escalation as required including crisis management, possibly BCP invocation
- Logging all response activities
- Communicating incident details to relevant internal and external parties (need-to-know)
- Coordinating with internal and external parties (authorities, interest groups, suppliers, clients)
- Formally closing and recording the incident
- Conducting IS forensic analysis as required
- Post-incident analysis: root cause identification; documentation and communication

---

## 5.27 Learning from Information Security Incidents
**Attributes:** #Corrective | #CIA | #Respond #Recover | #Information_security_event_management | #Defence #Resilience

**Purpose:** Reduce likelihood or consequences of future incidents.

**Key Points:**
- Establish procedures to quantify and monitor types, volumes, and costs of IS incidents
- Use evaluation information to:
  - Enhance incident management plan including scenarios and procedures
  - Identify recurring or serious incidents and causes; update risk assessments; determine/implement additional controls
  - Enhance user awareness and training: examples, how to respond, how to avoid

---

## 5.28 Collection of Evidence
**Attributes:** #Corrective | #CIA | #Respond | #Information_security_event_management | #Defence

**Purpose:** Ensure consistent and effective management of evidence for disciplinary and legal actions.

**Key Points:**
- Develop and follow internal procedures for dealing with evidence
- Consider different jurisdictions' requirements
- Procedures for: identification, collection, acquisition, preservation of evidence across storage media types and device states
- Evidence must be admissible: records are complete and untampered; copies identical to originals; systems were operating correctly when evidence was recorded
- Seek certification/qualification of personnel and tools
- For digital evidence crossing jurisdictional boundaries: ensure organization is entitled to collect

---

## 5.29 Information Security During Disruption
**Attributes:** #Preventive #Corrective | #CIA | #Protect #Recover | #Continuity | #Resilience

**Purpose:** Protect information and other associated assets during disruption.

**Key Points:**
- Determine requirements for adapting IS controls during disruption
- Include IS requirements in business continuity management processes
- Develop, implement, test, review, evaluate plans to maintain or restore IS of critical business processes
- Restore IS at required level within required time frames
- Implement and maintain: IS controls, supporting systems, and tools within BCP/ICT continuity plans; processes to maintain existing IS controls during disruption; compensating controls for controls that cannot be maintained
- Consider loss of confidentiality and integrity (not just availability) in BIA and risk assessments

---

## 5.30 ICT Readiness for Business Continuity ⭐ NEW IN 2022
**Attributes:** #Preventive | #Availability | #Protect #Recover | #Continuity | #Resilience

**Purpose:** Ensure availability of organization's information and other associated assets during disruption.

**Key Points:**
- Identify ICT continuity requirements through BIA
- BIA: use impact types and criteria to assess disruption impacts
- Use BIA results to identify prioritized activities with Recovery Time Objectives (RTO)
- Determine ICT resources needed to support prioritized activities
- Define performance/capacity requirements and Recovery Point Objectives (RPO)
- Based on BIA and risk assessment: identify and select ICT continuity strategies for before, during, and after disruption
- Develop, implement, and test plans to meet availability requirements

**Plans should include:**
- Performance and capacity specifications
- RTO of each prioritized ICT service and restoration procedures
- RPO of prioritized ICT resources and information restoration procedures

---

## 5.31 Legal, Statutory, Regulatory and Contractual Requirements
**Attributes:** #Preventive | #CIA | #Identify | #Legal_and_compliance | #Governance_and_Ecosystem

**Purpose:** Ensure compliance with legal, statutory, regulatory, and contractual requirements related to IS.

**External requirements should be considered when:**
- Developing IS policies and procedures
- Designing, implementing, or changing IS controls
- Classifying information and other assets
- Performing IS risk assessments
- Determining processes, roles, and responsibilities
- Determining suppliers' contractual requirements

**Organization should:**
- Identify all relevant legislation and regulations
- Consider compliance in all relevant countries where business is conducted
- Consider information transfers across jurisdictional borders
- Regularly review to remain current
- Define specific processes and individual responsibilities

---

## 5.32 Intellectual Property Rights
**Purpose:** Ensure compliance with legal, statutory, regulatory, and contractual requirements related to IPR.

**Key Points:**
- Define and communicate topic-specific policy on protection of IPR
- Acquire software only through known and reputable sources
- Maintain asset registers identifying all assets with IPR requirements
- Maintain proof and evidence of ownership of licenses
- Ensure max users/resources within license not exceeded
- Carry out reviews to ensure only authorized and licensed products are installed
- Provide procedures for maintaining license conditions
- Provide procedures for disposing/transferring software
- Comply with terms for software from public networks
- Do not duplicate/convert/extract from commercial recordings beyond what is permitted

---

## 5.33 Protection of Records
**Purpose:** Ensure compliance with legal, statutory, regulatory, and contractual requirements related to protection and availability of records.

**Key Points:**
- Issue guidelines on storage, handling, chain of custody, and disposal
- Draw up retention schedule defining records and retention periods
- Establish storage/handling system for identification and retention period tracking
- Categorize records into types (accounting, business transaction, personnel, legal) with retention periods and allowable storage media
- Choose data storage systems where required records can be retrieved in acceptable time and format
- Electronic storage: establish procedures for access throughout retention period
- Retain related cryptographic keys and programs associated with encrypted archives for retention period length

---

## 5.34 Privacy and Protection of PII
**Purpose:** Ensure compliance with legal, statutory, regulatory, and contractual requirements related to IS aspects of PII protection.

**Key Points:**
- Establish and communicate topic-specific policy on privacy and PII protection
- Develop and implement procedures for preservation of privacy and protection of PII
- Communicate procedures to all relevant parties involved in processing PII
- Appoint responsible person (e.g., privacy officer) to provide guidance
- Handle PII responsibility per relevant legislation and regulations
- Implement appropriate technical and organizational measures

---

## 5.35 Independent Review of Information Security
**Purpose:** Ensure continuing suitability, adequacy, and effectiveness of organization's approach to managing IS.

**Key Points:**
- Establish processes to conduct independent reviews at planned intervals or when significant changes occur
- Reviews include: assessing improvement opportunities; need for changes to approach, policies, controls
- Reviews carried out by individuals independent of the area under review (internal audit, independent manager, or external party)
- Reviewers must have appropriate competence and not be in line of authority
- Report results to management who initiated review and, if appropriate, to top management
- If reviews identify inadequacy: initiate corrective actions

**Triggers for independent review:**
- Laws and regulations change
- Significant incidents occur
- Organization starts or changes a business
- New products or services adopted
- IS controls and procedures change significantly

---

## 5.36 Compliance with Policies, Rules and Standards for Information Security
**Purpose:** Ensure IS is implemented and operated per the organization's IS policies, topic-specific policies, rules, and standards.

**Key Points:**
- Managers/owners identify how to review that IS requirements are met
- Consider automatic measurement and reporting tools
- If non-compliance found: identify causes; evaluate need for corrective actions; implement actions; review effectiveness
- Record results of reviews and corrective actions
- Report results to persons carrying out independent reviews (5.35) when applicable
- Complete corrective actions in timely manner appropriate to risk

---

## 5.37 Documented Operating Procedures
**Purpose:** Ensure correct and secure operation of information processing facilities.

**Document when:**
- Activity needs to be performed the same way by many people
- Activity is performed rarely and procedure likely forgotten
- Activity is new and presents risk if not performed correctly
- Handing over to new personnel

**Procedures should specify:**
- Responsible individuals
- Secure installation and configuration of systems
- Processing and handling of information (automated and manual)
- Backup and resilience
- Scheduling requirements including interdependencies
- Instructions for handling errors and exceptional conditions
- Support and escalation contacts
- Storage media handling instructions
- System restart and recovery procedures
- Management of audit trail and system log information
- Monitoring procedures (capacity, performance, security)
- Maintenance instructions
