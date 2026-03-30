# Handala Hack / Void Manticore - Threat Briefing
**Date:** 2026-03-29
**Classification:** DIB-Relevant | CRITICAL
**Confidence:** B (FBI + Check Point Research)

## Executive Summary
Iranian MOIS-affiliated threat actor conducting destructive operations and hack-and-leak campaigns. **Direct threat to DIB organizations** - especially those with IT/service provider relationships to government or healthcare sectors.

## Actor Profile
| Attribute | Value |
|-----------|-------|
| **aka** | Void Manticore, Red Sandstorm, Banished Kitten, Karma, Homeland Justice |
| **Country** | Iran (MOIS) |
| **Type** | APT - Destructive/Espionage |
| **Risk Level** | CRITICAL |
| **Active Since** | Late 2023 |
| **Last Activity** | March 2026 (Stryker attack) |

## Target Profile
Primary targeting relevant to DIB customers:
- **IT/Service Providers** - Supply chain access vector
- **Defense Industrial Base** - Direct targeting suspected
- **Healthcare** - Medical technology (Stryker)
- **Government** - Dissidents, journalists, opposition groups
- **Telecommunications** - Albania, Israel, US

## Key TTPs (MITRE ATT&CK)

### Initial Access
- **Compromised VPN credentials** - Primary entry vector
- **T1133 - External Remote Services** - Targeting VPN infrastructure
- **T1078.002 - Valid Accounts** - Stolen domain credentials
- **T1199 - Trusted Relationship** - IT/service provider targeting

### Credential Access
- **T1110 - Brute Force** - Logon attempts against VPN
- **T1003.001 - LSASS Dumping** - via comsvcs.dll / rundll32
- **T1003.002 - SAM Registry Export** - Credential extraction

### Lateral Movement
- **T1021.001 - RDP** - Manual, hands-on movement
- **T1572 - Protocol Tunneling** - NetBird mesh VPN for internal access
- **T1087.002 - ADRecon** - Active Directory enumeration

### Execution
- **T1059.001 - PowerShell** - AI-assisted wiping script
- **T1047 - WMI** - Lateral movement commands
- **T1484.001 - GPO Modification** - Wiper distribution
- **T1037.003 - Network Logon Scripts** - Trigger destructive components
- **T1053.005 - Scheduled Tasks** - Wiper deployment

### Impact
- **T1561.002 - Disk Structure Wipe** - MBR-based corruption
- **T1485 - Data Destruction** - File deletion, manual wiping
- **T1486 - Data Encrypted for Impact** - VeraCrypt disk encryption

## Recent Activity
**March 2026:** Attack on US medical technology giant **Stryker**. Used multi-stage malware with Telegram C2 for data exfiltration. Destructive wiping via custom malware and PowerShell.

**Key development:** Actor now connecting directly from Iranian IP addresses (including Starlink) - operational security has degraded since start of Israel-Iran conflict.

## IOCs

### IP Addresses
| IP | Description | Confidence |
|----|-------------|------------|
| 82.25.35.25 | Handala VPS | B |
| 31.57.35.223 | Handala VPS | B |
| 107.189.19.52 | C2 server | B |
| 146.185.219.235 | VPN exit node | B |
| 149.88.26.0/24 | Commercial VPN | C |
| 169.150.227.0/24 | Commercial VPN | C |
| 188.92.255.0/24 | Starlink | C |
| 209.198.131.0/24 | Starlink | C |

### Malware
| Hash | Description | Confidence |
|------|-------------|------------|
| 5986ab04dd6b3d259935249741d3eff2 | Handala Wiper | B |
| 3cb9dea916432ffb8784ac36d1f2d3cd | Handala PowerShell Wiper | B |
| 3236facc7a30df4ba4e57fddfba41ec5 | VeraCrypt Installer | B |
| 3dfb151d082df7937b01e2bb6030fe4a | NetBird Installer | B |

## DIB Relevance

### Why DIB Organizations Should Care
1. **IT service provider targeting** - If you serve government/DIB clients, you're in the supply chain
2. **Compromised credentials** - MFA gaps on VPNs are a primary vector
3. **Destructive capability** - Not just espionage; they wipe. Backup integrity is critical.
4. **Starlink abuse** -geo-blocking Starlink is no longer sufficient

### Immediate Actions for DIB Clients
- [ ] Audit VPN credentials, enforce MFA, check for unauthorized access
- [ ] Review backup integrity and offline/offsite backup coverage
- [ ] Block Iranian IP ranges at perimeter (see IOCs)
- [ ] Implement conditional access for high-risk geographies
- [ ] Monitor for ADRecon execution (dra.ps1)
- [ ] Hunt for NetBird installations (legitimate tool, abused for tunneling)
- [ ] Review group policy logon scripts for unauthorized changes

## Detection Queries

### Sentinel/KQL - VPN Brute Force
```
SigninLogs
| where ResultType != 0
| where IPAddress has "149.88" or IPAddress has "169.150"
| summarize attempt_count = count() by UserPrincipalName, IPAddress, Location
| where attempt_count > 5
```

### Sentinel/KQL - LSASS Dump
```
SecurityEvent
| where EventID == 10
| where CommandLine contains "comsvcs.dll"
```

### Sentinel/KQL - NetBird Tunnel
```
NetworkConnection
| where RemotePort == "443" and RemoteIP has "NetBird"
| or ProcessName contains "netbird"
```

## Sources
- FBI Attribution Report (March 2026)
- Check Point Research: "Handala Hack - Unveiling Group's Modus Operandi" (March 2026)
- Infosecurity Magazine: "Handala Group Tied to Iranian Hack-and-Leak Operations" (March 2026)

## Reliability Rating: B
Multiple independent sources (FBI + Check Point). High-confidence attribution to MOIS.
