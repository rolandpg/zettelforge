# ISO/IEC 27002:2022 — Technological Controls (8.1–8.34)

**34 controls | Theme: Technological**

---

## 8.1 User Endpoint Devices
**Attributes:** #Preventive | #CIA | #Protect | #System_and_network_security | #Protection

**Purpose:** Protect information against risks introduced by using user endpoint devices.

**Key Points:**
- Topic-specific policy covering: info type/classification the device can handle; registration requirements; physical protection; software installation restrictions; update requirements; rules for connecting to public networks; access controls; storage device encryption; malware protection; remote disabling/deletion/lockout; backups; web service usage; end user behavior analytics; removable devices; partitioning capabilities
- Consider whether sensitive information should only be accessed via endpoint, not stored on it
- Enforce through configuration management or automated tools
- Advise users: log off active sessions; protect with physical and logical controls; care in public places; physically protect against theft
- Procedures for theft or loss of devices
- BYOD: separate personal and business use; access only after acknowledgement of duties; allow remote wiping; address IP disputes
- Establish wireless connection procedures

---

## 8.2 Privileged Access Rights
**Attributes:** #Preventive | #CIA | #Protect | #Identity_and_access_management | #Protection

**Purpose:** Ensure only authorized users, software components, and services are provided with privileged access rights.

**Key Points:**
- Formal authorization process for all privileged access allocation
- Identify users needing privileged access per system/process
- Allocate on a need and event-by-event basis (minimum for functional role)
- Maintain authorization process and record of all allocated privileges
- Define and implement expiry requirements for privileged access rights
- Ensure users are aware when they are in privileged access mode
- Apply higher authentication requirements (re-authentication or step-up)
- Regularly review to verify continued qualification
- Avoid generic administration IDs (e.g., "root")
- Grant temporary privileged access only for necessary time window (break-glass procedure)
- Log all privileged access to systems
- Do not share privileged identities among multiple persons
- Use privileged identities only for administrative tasks, not day-to-day activities (email, browsing)

---

## 8.3 Information Access Restriction
**Attributes:** #Preventive | #CIA | #Protect | #Identity_and_access_management | #Protection

**Purpose:** Ensure only authorized access and prevent unauthorized access.

**Key Points:**
- Restrict access per established topic-specific access control policies
- Do not allow access by unknown user identities or anonymously to sensitive information
- Control which data can be accessed by which user
- Control identity/group access rights (read, write, delete, execute)
- Physical or logical access controls for isolation of sensitive applications, data, or systems
- Consider dynamic access management for: granular control over access timing/method; sharing externally while maintaining control; real-time management; protection against unauthorized changes/copying; monitoring information use
- Dynamic access management systems should: require authentication/credentials/certificates; restrict by time frame; use encryption; define printing permissions; record access; raise alerts on misuse

---

## 8.4 Access to Source Code
**Attributes:** #Preventive | #Confidentiality #Integrity | #Protect | #Application_security | #Protection

**Purpose:** Prevent introduction of unauthorized functionality, avoid unintentional or malicious changes, maintain confidentiality of intellectual property.

**Key Points:**
- Strictly control access to source code and associated items (designs, specs, verification/validation plans) and dev tools (compilers, builders, integration tools, test platforms)
- Use central storage (source code management system)
- Differentiate read and write access by role; write access only to privileged personnel or designated owners
- Manage access per established procedures
- Grant read/write access based on business needs aligned with risk of alteration or misuse
- Update source code and grant access only after appropriate authorization per change control
- Don't grant developers direct access to repository; use dev tools that control activities and authorizations
- Maintain audit log of all accesses and changes to source code
- Consider digital signatures for source code intended to be published

---

## 8.5 Secure Authentication
**Attributes:** #Preventive | #CIA | #Protect | #Identity_and_access_management | #Protection

**Purpose:** Ensure a user or entity is securely authenticated when access to systems, applications, and services is granted.

**Key Points:**
- Choose authentication techniques appropriate to classification of information being accessed
- For critical systems: use multi-factor authentication (what you know + what you have + what you are)
- Alternatives to passwords for strong auth: digital certificates, smart cards, tokens, biometric means
- MFA can be combined with contextual rules (unusual location, device, time)
- Biometric authentication information should be invalidable if compromised; accompany with at least one alternative

**Log-on procedures should:**
- Not display sensitive system information until log-on is successfully completed
- Display warning that only authorized users should access the system
- Not provide help messages that would aid unauthorized users
- Validate log-on information only upon completion of all input data
- Protect against brute force (CAPTCHA, password reset after failed attempts, user blocking)
- Log unsuccessful and successful attempts
- Raise security events for potential breaches
- Display date/time of previous successful log-on and details of unsuccessful attempts
- Not display passwords in clear text
- Not transmit passwords in clear text over network
- Terminate inactive sessions after defined period
- Restrict connection duration for high-risk applications

---

## 8.6 Capacity Management
**Attributes:** #Preventive | #Availability | #Protect | #System_and_network_security | #Protection

**Purpose:** Ensure required capacity of information processing facilities, human resources, offices, and other facilities.

**Key Points:**
- Identify capacity requirements for processing facilities, HR, offices, and other facilities based on business criticality
- Apply system tuning and monitoring to ensure and improve availability and efficiency
- Perform stress tests to confirm sufficient capacity for peak performance
- Put detective controls in place to indicate problems in timely manner
- Account for new business/system requirements and projected trends in future capacity planning
- Pay particular attention to long-lead or high-cost resources

**Capacity increase options:** hiring, new facilities, more powerful systems, cloud computing (elasticity/scalability)
**Demand reduction options:** delete obsolete data, dispose of hardcopy records, decommission apps/systems/DBs, optimize batch processes, optimize application code/DB queries, deny/restrict bandwidth for non-critical resource-consuming services

- Document capacity management plan for mission critical systems

---

## 8.7 Protection Against Malware
**Attributes:** #Preventive #Detective | #CIA | #Protect #Detect | #Threat_and_vulnerability_management | #Defence

**Purpose:** Ensure information and other associated assets are protected against malware.

**Key Points:**
- Protection should include: malware detection/repair software; IS awareness; appropriate system access; change management controls (detection software alone is not sufficient)
- Implement rules to prevent or detect use of unauthorized software (application allowlisting)
- Implement controls to prevent or detect use of known/suspected malicious websites (blocklisting)
- Reduce vulnerabilities exploitable by malware through technical vulnerability management
- Regular automated validation of software and data content, especially for critical business processes
- Establish protective measures for files from external networks or media
- Install and regularly update malware detection/repair software; carry out regular scans including: data received over networks/media; email and IM attachments and downloads; webpages when accessed
- Placement and configuration of tools based on risk assessment; consider defence-in-depth and attacker evasion techniques
- Protect against malware introduction during maintenance and emergency procedures
- Implement process to authorize temporarily/permanently disabling malware measures when causing operational disruption
- Prepare BCP for recovering from malware attacks including all necessary data and software backup
- Isolate environments where catastrophic consequences can occur
- Define procedures and responsibilities for malware protection
- Provide awareness and training on how to identify and mitigate malware
- Implement procedures to regularly collect information about new malware
- Verify malware information comes from qualified and reputable sources

---

## 8.8 Management of Technical Vulnerabilities
**Attributes:** #Preventive #Corrective | #CIA | #Identify #Protect | #Threat_and_vulnerability_management | #Defence

**Purpose:** Prevent exploitation of technical vulnerabilities.

**Identifying vulnerabilities:**
- Maintain accurate asset inventory (vendor, name, version, deployment state, responsible person) as prerequisite
- Define roles/responsibilities: monitoring, risk assessment, updating, asset tracking, coordination
- Identify information resources for vulnerability identification; update based on inventory changes
- Require suppliers to ensure vulnerability reporting, handling, disclosure in contracts
- Use vulnerability scanning tools suitable for technologies in use
- Conduct planned, documented, repeatable penetration tests or vulnerability assessments
- Track third-party libraries and source code for vulnerabilities
- Develop procedures to detect vulnerabilities and receive vulnerability reports
- Provide public point of contact for vulnerability disclosure; consider bug bounty programs

**Evaluating vulnerabilities:**
- Analyze and verify reports to determine response and remediation
- Identify associated risks and actions

**Taking measures:**
- Implement software update management process ensuring most up-to-date approved patches are installed
- Take appropriate and timely action; define timeline to react
- Only use updates from legitimate sources
- Test and evaluate updates before installation
- Address high-risk systems first
- Develop remediation; test effectiveness; provide mechanisms to verify authenticity
- If no update is available: apply vendor workarounds; turn off related services; adapt/add access controls; shield with traffic filters (virtual patching); increase monitoring; raise awareness
- Keep audit log for all steps undertaken
- Regularly monitor and evaluate effectiveness and efficiency
- Align with incident management activities

---

## 8.9 Configuration Management ⭐ NEW IN 2022
**Attributes:** #Preventive | #CIA | #Protect | #Secure_configuration | #Protection

**Purpose:** Ensure hardware, software, services, and networks function correctly with required security settings; configuration is not altered by unauthorized or incorrect changes.

**Standard templates:**
- Define standard templates for secure configuration using: publicly available guidance; appropriate level of protection needed; support for IS policies; feasibility and applicability
- Review and update templates periodically for new threats/vulnerabilities
- Templates should address: minimizing privileged/admin identities; disabling unnecessary identities; disabling/restricting unnecessary functions and services; restricting access to utility programs; synchronizing clocks; changing vendor default authentication info immediately after installation; invoking time-out facilities; verifying license requirements

**Managing configurations:**
- Record established configurations and log all changes; store records securely
- Follow change management process for configuration changes
- Configuration records should include: owner/contact info; date of last change; version of config template; relation to configurations of other assets

**Monitoring configurations:**
- Use comprehensive system management tools
- Review regularly to verify settings; evaluate password strengths; assess activities
- Compare actual configurations with defined target templates
- Address deviations automatically or through manual analysis and corrective actions

---

## 8.10 Information Deletion ⭐ NEW IN 2022
**Attributes:** #Preventive | #Confidentiality | #Protect | #Information_protection | #Protection #Defence

**Purpose:** Prevent unnecessary exposure of sensitive information and comply with legal, statutory, regulatory, and contractual requirements for deletion.

**Key Points:**
- Do not keep sensitive information longer than required
- When deleting from systems, applications, and services: select appropriate deletion method (electronic overwriting or cryptographic erasure); record results as evidence; obtain evidence from third-party deletion service suppliers
- Include information deletion requirements in third-party agreements
- Per data retention policies and legislation, delete sensitive information by:
  - Configuring systems to securely destroy information when no longer required
  - Deleting obsolete versions, copies, and temporary files
  - Using approved, secure deletion software (info cannot be recovered by specialist tools)
  - Using approved, certified providers of secure disposal services
  - Using disposal mechanisms appropriate for storage media type (degaussing for magnetic media)
- For cloud services: verify if deletion method is acceptable; use it or request provider delete; automate deletion processes
- Protect sensitive info before sending equipment back to vendors: remove auxiliary storage and memory
- For devices where secure deletion only achievable through destruction or embedded functions ("restore factory settings"): choose method based on classification
- Maintain official records of information deletion for potential leakage analysis

---

## 8.11 Data Masking ⭐ NEW IN 2022
**Attributes:** #Preventive | #Confidentiality | #Protect | #Information_protection | #Protection

**Purpose:** Limit exposure of sensitive data including PII; comply with legal, statutory, regulatory, and contractual requirements.

**Key Points:**
- Where sensitive data protection is a concern: consider data masking, pseudonymization, or anonymization
- Pseudonymization/anonymization can: hide PII; disguise true identity of PII principals; disconnect links between PII and identity
- Verify that data has been adequately pseudonymized/anonymized; consider all elements; note indirect identification is still possible
- Additional masking techniques: encryption (requiring key); nulling or deleting characters; varying numbers and dates; substitution; replacing values with hash

**Implementation considerations:**
- Design queries and masks to show only minimum required data
- Implement obfuscation mechanisms for data that should not be visible in certain records
- Give PII principals the possibility to require that users cannot see if data is obfuscated
- Consider legal or regulatory requirements
- Prohibit collating processed data with other information to identify PII principals
- Keep track of providing and receiving processed data

**Definitions:**
- **Anonymization:** Irreversibly alters PII so the PII principal can no longer be identified
- **Pseudonymization:** Replaces identifying information with an alias; "additional information" used to perform pseudonymization should be kept separate and protected
- Hash functions used for anonymization should always be combined with a salt function to prevent enumeration attacks

---

## 8.12 Data Leakage Prevention ⭐ NEW IN 2022
**Attributes:** #Preventive #Detective | #Confidentiality #Integrity | #Protect #Detect | #Information_protection | #Defence #Protection

**Purpose:** Detect and prevent unauthorized disclosure and extraction of information.

**Key Points:**
- Identify and classify information to protect against leakage
- Monitor channels of data leakage: email, file transfers, mobile devices, portable storage devices
- Act to prevent information from leaking (e.g., quarantine emails containing sensitive info)
- Use DLP tools to: identify and monitor sensitive information at risk; detect disclosure; block user actions or network transmissions that expose sensitive information
- Determine if necessary to restrict users' ability to copy/paste or upload data to external services; implement technology to allow viewing/manipulation but prevent copy/paste outside organizational control
- If data export is required: allow data owner to approve; hold users accountable
- Address screenshots/photographs through terms and conditions, training, and auditing
- Ensure backed-up data is protected: encryption, access control, physical protection of backup storage media
- Consider DLP against intelligence actions of adversaries: replacing authentic info with false info; reverse social engineering; honeypots

---

## 8.13 Information Backup
**Attributes:** #Preventive #Corrective | #CIA | #Protect #Recover | #Continuity | #Resilience

**Purpose:** Enable recovery from loss of data or systems.

**Key Points:**
- Establish topic-specific policy on backup addressing data retention and IS requirements
- Provide adequate backup facilities for all essential information and software recovery
- When designing backup plan consider:
  - Accurate and complete records of backup copies and documented restoration procedures
  - Backup extent and frequency reflecting business requirements (RPO), security requirements, and criticality
  - Storing backups in secure, remote location at sufficient distance to escape damage from disasters at main site
  - Backup information given appropriate physical and environmental protection consistent with main site standards
  - Testing backup media regularly to ensure it can be relied on for emergency use
  - Testing restoration procedures to ensure effective and within time allocated in operational procedures for recovery
  - Protecting backups per classification level
  - Considering use of immutable storage for backup data to defend against ransomware
  - Logging activities
  - Considering full, incremental, differential, or snapshot approaches
  - Considering off-site storage, cloud storage
  - System-level backups including: OS; applications and configuration; data

---

## 8.14 Redundancy of Information Processing Facilities
**Attributes:** #Preventive | #Availability | #Protect | #Continuity | #Resilience

**Purpose:** Ensure continuous operation of information processing facilities.

**Key Points:**
- Identify availability requirements for business services and information systems
- Design and implement systems architecture with appropriate redundancy
- Introduce redundancy by duplicating information processing facilities (in part or entirety)
- Plan and implement procedures for activation of redundant components
- Consider: multiple network/ISP contracts; redundant networks; geographically separate data centres; redundant power supplies; multiple parallel software instances; duplicated hardware components
- Test redundant systems preferably in production mode to ensure failover works as intended
- Redundant components must maintain the same security level as primary components

---

## 8.15 Logging
**Attributes:** #Detective | #CIA | #Detect | #Information_security_event_management | #Defence

**Purpose:** Record events, generate evidence, ensure log integrity, prevent unauthorized access, identify IS events, and support investigations.

**Event logs should include:**
- User IDs
- System activities
- Dates, times, and details of relevant events
- Device identity, system identifier, and location
- Network addresses and protocols

**Events to consider for logging:**
- Successful and rejected system/data access attempts
- Changes to system configuration
- Use of privileges and utility programs
- Files accessed and type of access
- Activation/deactivation of security systems
- Creation, modification, or deletion of identities

**Protection of logs:**
- Users (including privileged) must not be able to delete or deactivate their own activity logs
- Protect against unauthorized changes: cryptographic hashing, append-only files, or public transparency files
- Some audit logs may require archiving for evidence retention purposes

**Log analysis:**
- Analyze for unusual activity or anomalous behaviour
- Use SIEM tools, UEBA, and threat intelligence
- Correlate logs for efficient and accurate analysis
- Review DNS logs, service provider usage reports, physical monitoring logs

---

## 8.16 Monitoring Activities ⭐ NEW IN 2022
**Attributes:** #Detective | #CIA | #Detect | #Information_security_event_management | #Defence

**Purpose:** Detect anomalous behaviour and potential IS incidents.

**Key Points:**
- Determine monitoring scope per business and IS requirements
- Monitor: network/system/application traffic; access to systems; configuration files; security tool logs; event logs; resource utilization
- Establish baseline of normal behaviour; monitor against it for anomalies
- **Anomalous behaviour to detect:**
  - Unplanned process termination
  - Malware-associated activity
  - Known attack characteristics
  - Unusual system behaviour
  - Bottlenecks/overloads
  - Unauthorized access attempts
  - Unusual scanning
- Use continuous, real-time monitoring tools capable of handling large data volumes
- Configure automated alerts based on predefined thresholds
- Maintain procedures to respond to alerts and address false positives
- Enhance with: threat intelligence; machine learning; blocklists/allowlists; penetration testing results; performance monitoring systems

---

## 8.17 Clock Synchronization
**Attributes:** #Preventive | #Integrity | #Protect | #System_and_network_security | #Protection #Defence

**Purpose:** Enable correlation and analysis of security-related events and other recorded data; support investigations.

**Key Points:**
- Document and implement external and internal requirements for time representation, synchronization, and accuracy
- Define standard reference time for use within the organization for all systems (including building management and entry/exit systems)
- Use a clock linked to national atomic clock or GPS as reference clock
- Use NTP or PTP protocols to keep all networked systems synchronized
- Consider using two external time sources simultaneously for improved reliability
- When using multiple cloud services: monitor clock of each service; record differences to mitigate risks from discrepancies

---

## 8.18 Use of Privileged Utility Programs
**Attributes:** #Preventive | #CIA | #Protect | #Identity_and_access_management | #Protection

**Purpose:** Ensure use of utility programs does not harm system and application controls.

**Key Points:**
- Limit use to minimum number of trusted, authorized users
- Use identification, authentication, and authorization procedures with unique user identification
- Define and document authorization levels
- Require authorization for ad hoc use
- Do not make available to users with application access where SoD is required
- Remove or disable all unnecessary utility programs
- At minimum, logically segregate utility programs from application software
- Limit availability (e.g., only for duration of authorized change)
- Log all use of utility programs

---

## 8.19 Installation of Software on Operational Systems
**Attributes:** #Preventive | #CIA | #Protect | #Secure_configuration | #Protection

**Purpose:** Ensure integrity of operational systems and prevent exploitation of technical vulnerabilities.

**Key Points:**
- Only trained administrators with management authorization should perform updates
- Only approved executable code; no development code or compilers on operational systems
- Install and update only after extensive and successful testing
- Update all corresponding program source libraries
- Use configuration control system for all operational software
- Define rollback strategy before implementing changes
- Maintain audit log of all updates
- Archive old versions as contingency measure
- Decisions to upgrade should consider business requirements and security of the release
- Monitor and control externally supplied software and packages
- Maintain vendor-supported software levels; assess risks of unsupported or open source software
- Apply principle of least privilege for software installation

---

## 8.20 Networks Security
**Attributes:** #Preventive #Detective | #CIA | #Protect #Detect | #System_and_network_security | #Protection

**Purpose:** Protect information in networks and its supporting facilities from compromise via the network.

**Key Points:**
- Consider type and classification level of information the network supports
- Establish responsibilities and procedures for management of networking equipment
- Maintain up-to-date documentation including network diagrams and configuration files
- Separate operational responsibility for networks from ICT system operations where appropriate
- Establish controls to safeguard CIA of data passing over public/third-party/wireless networks
- Appropriately log and monitor actions affecting IS
- Authenticate systems on the network
- Restrict and filter system connections (firewalls)
- Detect, restrict, and authenticate connection of equipment and devices
- Harden network devices; segregate network administration channels
- Temporarily isolate critical subnetworks if under attack
- Disable vulnerable network protocols
- Apply security controls to virtualized networks (SDN, SD-WAN)

---

## 8.21 Security of Network Services
**Attributes:** #Preventive | #CIA | #Protect | #System_and_network_security | #Protection

**Purpose:** Ensure security in the use of network services.

**Key Points:**
- Identify and implement security measures for particular services (security features, service levels, requirements)
- Ensure network service providers implement required security measures
- Regularly monitor provider's ability to manage services securely; agree right to audit
- Consider third-party attestations from service providers
- Formulate and implement rules covering: permitted networks/services; authentication requirements; authorization procedures; network management controls; means of access (VPN, wireless); time/location attributes; monitoring
- Security features to consider: technology applied (authentication, encryption, connection controls); technical parameters; caching parameters; procedures to restrict access

---

## 8.22 Segregation of Networks
**Attributes:** #Preventive | #CIA | #Protect | #System_and_network_security | #Protection

**Purpose:** Split network into security boundaries and control traffic between them based on business needs.

**Key Points:**
- Divide large networks into separate network domains (physical or logical)
- Choose domains based on levels of trust, criticality, sensitivity, or organizational units
- Well-define the perimeter of each domain
- Control access between domains at perimeter using gateways (firewalls, filtering routers)
- Base segregation criteria on security requirements assessment per access control policy
- Wireless networks require special treatment (poorly defined perimeters)
- Consider treating all wireless access as external connections in sensitive environments
- Segregate guest wireless access from personnel wireless access
- Guest WiFi should have at least the same restrictions as personnel WiFi

---

## 8.23 Web Filtering ⭐ NEW IN 2022
**Attributes:** #Preventive #Detective | #CIA | #Protect #Detect | #System_and_network_security | #Protection #Defence

**Purpose:** Protect systems from malware compromise and prevent access to unauthorized web resources.

**Key Points:**
- Reduce risks of personnel accessing websites with illegal information, viruses, or phishing material
- Block IP addresses or domains of concerning websites
- Identify types of websites to block:
  - Websites with information upload functions (unless business-justified)
  - Known or suspected malicious websites
  - Command and control servers
  - Malicious websites identified through threat intelligence
  - Websites sharing illegal content
- Establish rules for safe and appropriate use of online resources before deploying the control
- Provide training on secure and appropriate use of online resources
- Train personnel not to override browser security advisories

---

## 8.24 Use of Cryptography
**Attributes:** #Preventive | #Confidentiality #Integrity | #Protect | #Information_protection | #Protection

**Purpose:** Ensure proper and effective use of cryptography to protect CIA of information per business and IS requirements.

**General:**
- Establish topic-specific policy on the use of cryptography
- Identify required level of protection and information classification to determine algorithm type, strength, and quality
- Consider cryptography for mobile devices, storage media, and network transmissions
- Define approach to key management
- Establish roles and responsibilities for cryptography implementation and key management
- Adopt approved cryptographic standards, algorithms, and cipher strengths
- Consider impact of encrypted information on content inspection controls
- Account for national regulations on cryptographic techniques and trans-border flow of encrypted information

**Key Management:**
- Establish secure processes for: generating, storing, archiving, retrieving, distributing, retiring, and destroying cryptographic keys
- Key management system should address: key generation; issuing/obtaining certificates; distributing keys; storing keys; changing/updating keys; handling compromised keys; revoking keys; recovering lost/corrupted keys; backing up/archiving; destroying keys; logging/auditing; setting activation/deactivation dates; handling legal requests
- Protect all cryptographic keys against modification and loss
- Physically protect equipment used to generate, store, and archive keys

---

## 8.25 Secure Development Life Cycle
**Attributes:** #Preventive | #CIA | #Protect | #Application_security | #Protection

**Purpose:** Ensure IS is designed and implemented within the secure development life cycle.

**Key Points:**
- Separate development, test, and production environments
- Apply security in the software development methodology and secure coding guidelines
- Address security requirements in specification and design phase
- Establish security checkpoints in projects
- Conduct system and security testing (regression testing, code scan, penetration tests)
- Maintain secure repositories for source code and configuration
- Implement security in version control
- Require application security knowledge and training
- Develop capability to prevent, find, and fix vulnerabilities
- Address licensing requirements
- Obtain assurance from outsourced developers that they comply with secure development rules

---

## 8.26 Application Security Requirements
**Attributes:** #Preventive | #CIA | #Identify | #Application_security | #Protection

**Purpose:** Ensure all IS requirements are identified and addressed when developing or acquiring applications.

**General requirements to include:**
- Level of trust in entity identity (authentication)
- Type and classification level of information processed
- Segregation of access and level of access to data and functions
- Resilience against malicious attacks (buffer overflow, SQL injection)
- Legal, statutory, and regulatory requirements
- Privacy requirements for all parties
- Protection of confidential information
- Data protection in processing, transit, and at rest
- Encryption requirements for communications
- Input controls, integrity checks, and input validation
- Automated controls and output controls
- Restrictions on free-text fields
- Non-repudiation requirements
- Interfaces to logging, monitoring, and data leakage detection

**Transactional services:** Trust levels; integrity mechanisms; authorization processes; confidentiality; non-repudiation; insurance requirements

**Electronic ordering and payment:** Confidentiality/integrity of order information; payment verification; avoiding transaction duplication; secure storage of transaction details

---

## 8.27 Secure System Architecture and Engineering Principles
**Attributes:** #Preventive | #CIA | #Protect | #Application_security | #Protection

**Purpose:** Ensure IS is securely designed, implemented, and operated within the development lifecycle.

**Key Points:**
- Establish, document, and apply security engineering principles to information system engineering activities
- Design security into all architecture layers (business, data, applications, technology)
- Analyze new technology for security risks; review designs against known attack patterns
- Secure engineering principles should analyze: full range of required security controls; capabilities; specific controls for business processes; where/how controls are applied; how controls work together

**Secure system engineering should involve:**
- Security architecture principles: "security by design"; "defence in depth"; "security by default"; "least privilege"; "assume breach"
- Security-oriented design reviews
- Documentation of non-compliant controls
- Hardening of systems

**Zero Trust principles:**
- Assume systems are already breached; don't rely solely on perimeter security
- "Never trust, always verify"
- Encrypt all requests end-to-end
- Verify each request as if from an open external network
- Use least privilege and dynamic access control
- Always authenticate requesters and validate authorization requests

---

## 8.28 Secure Coding ⭐ NEW IN 2022
**Attributes:** #Preventive | #CIA | #Protect | #Application_security | #Protection

**Purpose:** Ensure software is written securely, reducing potential IS vulnerabilities.

**Planning and before coding:**
- Establish organization-wide secure coding governance processes
- Monitor real-world threats and up-to-date vulnerability information
- Define organization-specific expectations and approved principles for secure coding
- Address common and historical coding practices that lead to vulnerabilities
- Configure development tools (IDEs) to enforce secure code creation
- Qualify developers in writing secure code
- Apply secure design and architecture including threat modelling
- Use secure coding standards
- Use controlled development environments

**During coding:**
- Apply secure coding practices specific to programming languages used
- Use secure programming techniques (pair programming, refactoring, peer review, TDD)
- Use structured programming techniques
- Document code and remove programming defects
- Prohibit insecure design techniques (hard-coded passwords, unapproved code samples, unauthenticated web services)
- Conduct SAST processes to identify security vulnerabilities

**Review and maintenance:**
- Securely package and deploy updates
- Handle reported vulnerabilities (per 8.8)
- Log errors and suspected attacks; regularly review
- Protect source code against unauthorized access and tampering
- Manage external libraries: maintain inventory; regularly update; select/authorize well-vetted components

---

## 8.29 Security Testing in Development and Acceptance
**Attributes:** #Preventive | #CIA | #Protect | #Application_security #Information_security_assurance | #Protection

**Purpose:** Validate if IS requirements are met when applications or code are deployed to production.

**Key Points:**
- Thoroughly test and verify new systems, upgrades, and new versions during development
- Security testing should be integral part of system/component testing
- Test against functional and non-functional security requirements: security functions (auth, access restriction, cryptography); secure coding; secure configurations (OS, firewalls, security components)
- Test plans should include: schedule of activities/tests; inputs and expected outputs; criteria to evaluate results; decisions for further actions
- Leverage automated tools (code analysis, vulnerability scanners)
- For in-house development: perform code reviews, vulnerability scanning, and penetration testing
- For outsourced development: follow acquisition processes; evaluate products against security criteria before acquisition
- Perform testing in environments that match target production as closely as possible
- Multiple test environments may be established for different types of testing

---

## 8.30 Outsourced Development
**Attributes:** #Preventive | #CIA | #Protect | #Application_security #Supplier_relationships_security | #Protection

**Purpose:** Ensure IS measures required by the organization are implemented in outsourced system development.

**Key Points:**
- Communicate and agree requirements and expectations; continually monitor and review delivery
- Consider across entire external supply chain:
  - Licensing agreements, code ownership, and intellectual property rights
  - Contractual requirements for secure design, coding, and testing practices
  - Provision of threat model to external developers
  - Acceptance testing for quality and accuracy of deliverables
  - Evidence of minimum acceptable security and privacy capabilities
  - Evidence sufficient testing has been applied against malicious content and known vulnerabilities
  - Escrow agreements for source code
  - Contractual right to audit development processes and controls
  - Security requirements for development environment
  - Applicable legislation compliance (e.g., personal data protection)

---

## 8.31 Separation of Development, Test and Production Environments
**Attributes:** #Preventive | #CIA | #Protect | #Application_security | #Protection

**Purpose:** Protect production environment and data from compromise by development and test activities.

**Key Points:**
- Identify and implement necessary level of separation between production, testing, and development environments
- Adequately separate development and production systems (different domains, virtual or physical environments)
- Define, document, and implement rules and authorization for deployment from development to production
- Test changes in testing/staging before applying to production
- Avoid testing in production environments except in defined and approved circumstances
- Ensure compilers, editors, and development tools are not accessible from production systems when not required
- Display appropriate environment identification labels to reduce error risk
- Do not copy sensitive information into dev/testing environments unless equivalent controls provided
- Protect all environments: patch/update; secure configuration; control access; monitor changes; take backups
- A single person should not be able to make changes to both development and production without prior review and approval

---

## 8.32 Change Management
**Attributes:** #Preventive | #CIA | #Protect | #System_and_network_security | #Protection

**Purpose:** Preserve IS when executing changes.

**Key Points:**
- New systems and major changes should follow agreed rules and formal processes: documentation, specification, testing, quality control, and managed implementation
- Integrate change control procedures for ICT infrastructure and software
- Change control procedures should include:
  - Planning and assessing potential impact considering all dependencies
  - Authorization of changes
  - Communicating changes to relevant interested parties
  - Tests and acceptance testing
  - Implementation including deployment plans
  - Emergency and contingency considerations including fallback/rollback procedures
  - Maintaining records of all changes
  - When changes fail to deliver expected results: ability to abort and recover

---

## 8.33 Test Information
**Attributes:** #Preventive | #Confidentiality #Integrity | #Protect | #Information_protection | #Protection

**Purpose:** Ensure relevance of testing and protection of operational information used for testing.

**Key Points:**
- Select test information carefully; protect and control operational information used for testing
- Avoid using operational databases containing personal information or other sensitive information for testing purposes
- If operational information is to be used for testing:
  - Obtain approval of owner and management
  - Apply procedures to sanitize data to the degree required (anonymize/pseudonymize)
  - Ensure necessary access controls are in place
  - Comply with legal requirements when copies of test information are removed
- Consider use of synthetic data generators or anonymized copies of real data
- Operational software should not run in test environments unless that environment is equivalent to the operational environment in all relevant IS controls

---

## 8.34 Protection of Information Systems During Audit Testing
**Attributes:** #Preventive | #CIA | #Protect | #Information_security_assurance | #Protection #Governance_and_Ecosystem

**Purpose:** Minimise impact of audit and other assurance activities on operational systems and business processes.

**Key Points:**
- Agree audit activities with appropriate management; obtain authorization
- Scope and control requirements for technical audit tests, especially those with the potential to affect system availability
- Tests that can potentially affect system availability should be conducted outside business hours
- Comply with legislation relating to collection of evidence (5.28)
- Monitor and log all access for audit trails and reference
- All procedures, requirements, and responsibilities should be documented
- Access to audit tools should be restricted to prevent misuse or compromise
- Isolate audit tools (i.e., systems and software) from development and operational systems
- Protect against adversarial tests being exploited by adversaries
- Agree on requirements for accessing network traffic or accessing plaintext of encrypted sessions
- Auditors should have read-only access to software and data unless otherwise unavoidable
- If access other than read-only required: ensure separation from production systems; keep copies of files before testing; return original files and software after testing
