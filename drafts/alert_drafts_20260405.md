# X Content Drafts - 2026-04-05

## Draft 1: Axios npm Supply Chain Attack
**Topic:** UNC1069 Social Engineering of Axios Maintainer
**Target:** DIB / MSSP / DevSecOps

🚨 Supply Chain Alert | High Confidence
UNC1069 (North Korea-linked) used social engineering on an Axios maintainer to compromise the npm package.
T1195.001 → T1059
If you're pulling Axios in your CI/CD pipelines without strict version pinning and integrity checks, you are exposed. 
Your SBOM isn't enough if you don't monitor registry anomalies in real-time.
Source: Roland Fleet CTI | Reliability: A2
#SupplyChain #AppSec #ThreatIntel #DIB

## Draft 2: Zoho ManageEngine KEV Additions
**Topic:** Multiple Zoho ManageEngine CVEs added to KEV (CVE-2021-40539, CVE-2020-10189)
**Target:** MSSP / DIB operations

🚨 CISA KEV Update | CRITICAL
CISA just batched multiple Zoho ManageEngine vulnerabilities into the KEV (including CVE-2021-40539 & CVE-2020-10189).
These are classic APT initial access vectors for DIB perimeters.
If you're an MSSP managing Zoho for defense contractors, check your patch delta immediately. Don't wait for the compliance deadline.
Source: CISA / Roland Fleet CTI
#CMMC #MSSP #CVE #KEV
