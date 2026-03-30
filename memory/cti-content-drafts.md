### DRAFT 6: MOIS + Cyber Crime Nexus — Strategic Intel Thread
**Priority: HIGH | Status: PENDING APPROVAL**

**Source:** Check Point Research (2026-03-16)
**Reliability:** A

---

**POST 1/3:**

High confidence | Source: Check Point Research | Reliability: A

New intel: Iranian MOIS actors aren't just imitating cyber crime — they're actively using it.

This is a strategic shift:
- MOIS buys criminal malware (Rhadamanthys, CastleLoader)
- Uses ransomware brands (Qilin) as cover for state ops
- Shares infrastructure with criminal botnets (Tsundere/DinDoor)
- Gets deniability + capability + obfuscation simultaneously

This isn't hacktivism. It's hybrid warfare using the crime ecosystem.

---

**POST 2/3:**

High confidence | Source: Check Point Research | Reliability: A

Case study: Shamir Medical Center (Israel)

Attack initially looked like Qilin ransomware.
Reality: Iranian MOIS operation using Qilin infrastructure as cover.
Target: Israeli hospital. Pattern matches MOIS/Hezbollah hospital targeting since 2023.

The ransomware brand was camouflage. The objective was strategic espionage/destruction.

---

**POST 3/3:**

High confidence | Source: Check Point Research | Reliability: A

MOIS actors + shared infrastructure:

MuddyWater (MOIS) + Tsundere botnet + CastleLoader all share code-signing certs.

Cert Common Names used:
- "Amy Cherne"
- "Donald Gay"

SHA256 samples in the link below.

If you're hunting MuddyWater, look for these certificates. They're being shared across MOIS and criminal tooling.

Source: Check Point Research
Link: https://research.checkpoint.com/2026/iranian-mois-actors-the-cyber-crime-connection/

#threatintel #MOIS #MuddyWater #Iran #cybersecurity

---

### DRAFT 7: Rhadamanthys — MOIS Tool Now Commercial
**Priority: MEDIUM | Status: PENDING APPROVAL**

**Source:** Check Point Research
**Reliability:** A

---

Medium confidence | Source: Check Point Research | Reliability: A

Rhadamanthys infostealer: Used by Handala Hack (MOIS) and commercial threat actors alike.

Handala deploys it via phishing impersonating F5 updates and Israeli National Cyber Directorate.

This is how state actors get operational malware without building it themselves.

SHA256: aae017e7a36e016655c91bd01b4f3c46309bbe540733f82cce29392e72e9bd1f

Source: Check Point Research

#threatintel #Rhadamanthys #infostealer #Iran
