# CTI Alert Rules

Alert rules for CTI pipeline. Run via cron, output to this file + notify.

## Rules

### 1. Critical CVE Alert
- Trigger: New CVE with CVSS >= 9.0 in monitored sectors
- Monitored sectors: Technology, Defense, Healthcare, Finance, Energy, Government
- Action: Log alert + flag for social media

### 2. Brand Mention Alert
- Trigger: New IOC or mention containing "summit7", "summit 7", "summit7.us"
- Action: Log alert immediately

### 3. APT Activity Alert
- Trigger: New IOC linked to APT threat actor
- Action: Log alert + flag for research

### 4. Sector Targeting Alert
- Trigger: Any new IOC targeting monitored sectors
- Action: Log for trend analysis

## Output Format

```
## Alert: <type> | <timestamp>
**Severity:** <high|critical>
**Summary:** <one-liner>
**Source:** <source>
**Action:** <post|research|ignore>
```

## Execution

Run via cron:
```
0 6,18 * * * cd ~/cti-workspace && python manage.py run_alerts >> memory/cti-alerts.md 2>&1
```
## Alerts: 5 found | 2026-03-20T11:00:01.578471

### 🟠 APT_ACTIVITY | Severity: HIGH
**Summary:** APT activity: 4caa797130b5f7116f11c0b48013e430
**Description:** Linked to: UNC
**Source:** OTX/STIX
**Action:** RESEARCH

### 🟠 APT_ACTIVITY | Severity: HIGH
**Summary:** APT activity: 6272ef6ac1de8fb4bdd4a760be7ba5ed
**Description:** Linked to: UNC
**Source:** OTX/STIX
**Action:** RESEARCH

### 🟠 APT_ACTIVITY | Severity: HIGH
**Summary:** APT activity: c882d948d44a65019df54b0b2996677f
**Description:** Linked to: UNC
**Source:** OTX/STIX
**Action:** RESEARCH

### 🟠 APT_ACTIVITY | Severity: HIGH
**Summary:** APT activity: b6144f80b32b37393b2da565326cd5085c6842e1
**Description:** Linked to: UNC
**Source:** OTX/STIX
**Action:** RESEARCH

### 🟠 APT_ACTIVITY | Severity: HIGH
**Summary:** APT activity: 474b25badb40f524a7b2fe089e51eb7dbafd2e3e
**Description:** Linked to: UNC
**Source:** OTX/STIX
**Action:** RESEARCH

📭 No alerts ready for social media yet

## Alerts: 5 found | 2026-03-20T23:00:01.913218

### 🟠 APT_ACTIVITY | Severity: HIGH
**Summary:** APT activity: 4caa797130b5f7116f11c0b48013e430
**Description:** Linked to: UNC
**Source:** OTX/STIX
**Action:** RESEARCH

### 🟠 APT_ACTIVITY | Severity: HIGH
**Summary:** APT activity: 6272ef6ac1de8fb4bdd4a760be7ba5ed
**Description:** Linked to: UNC
**Source:** OTX/STIX
**Action:** RESEARCH

### 🟠 APT_ACTIVITY | Severity: HIGH
**Summary:** APT activity: c882d948d44a65019df54b0b2996677f
**Description:** Linked to: UNC
**Source:** OTX/STIX
**Action:** RESEARCH

### 🟠 APT_ACTIVITY | Severity: HIGH
**Summary:** APT activity: b6144f80b32b37393b2da565326cd5085c6842e1
**Description:** Linked to: UNC
**Source:** OTX/STIX
**Action:** RESEARCH

### 🟠 APT_ACTIVITY | Severity: HIGH
**Summary:** APT activity: 474b25badb40f524a7b2fe089e51eb7dbafd2e3e
**Description:** Linked to: UNC
**Source:** OTX/STIX
**Action:** RESEARCH

📭 No alerts ready for social media yet

## Alerts: 5 found | 2026-03-21T11:00:01.855079

### 🟠 APT_ACTIVITY | Severity: HIGH
**Summary:** APT activity: 4caa797130b5f7116f11c0b48013e430
**Description:** Linked to: UNC
**Source:** OTX/STIX
**Action:** RESEARCH

### 🟠 APT_ACTIVITY | Severity: HIGH
**Summary:** APT activity: 6272ef6ac1de8fb4bdd4a760be7ba5ed
**Description:** Linked to: UNC
**Source:** OTX/STIX
**Action:** RESEARCH

### 🟠 APT_ACTIVITY | Severity: HIGH
**Summary:** APT activity: c882d948d44a65019df54b0b2996677f
**Description:** Linked to: UNC
**Source:** OTX/STIX
**Action:** RESEARCH

### 🟠 APT_ACTIVITY | Severity: HIGH
**Summary:** APT activity: b6144f80b32b37393b2da565326cd5085c6842e1
**Description:** Linked to: UNC
**Source:** OTX/STIX
**Action:** RESEARCH

### 🟠 APT_ACTIVITY | Severity: HIGH
**Summary:** APT activity: 474b25badb40f524a7b2fe089e51eb7dbafd2e3e
**Description:** Linked to: UNC
**Source:** OTX/STIX
**Action:** RESEARCH

📭 No alerts ready for social media yet

## Alerts: 5 found | 2026-03-21T23:00:01.249529

### 🟠 APT_ACTIVITY | Severity: HIGH
**Summary:** APT activity: 4caa797130b5f7116f11c0b48013e430
**Description:** Linked to: UNC
**Source:** OTX/STIX
**Action:** RESEARCH

### 🟠 APT_ACTIVITY | Severity: HIGH
**Summary:** APT activity: 6272ef6ac1de8fb4bdd4a760be7ba5ed
**Description:** Linked to: UNC
**Source:** OTX/STIX
**Action:** RESEARCH

### 🟠 APT_ACTIVITY | Severity: HIGH
**Summary:** APT activity: c882d948d44a65019df54b0b2996677f
**Description:** Linked to: UNC
**Source:** OTX/STIX
**Action:** RESEARCH

### 🟠 APT_ACTIVITY | Severity: HIGH
**Summary:** APT activity: b6144f80b32b37393b2da565326cd5085c6842e1
**Description:** Linked to: UNC
**Source:** OTX/STIX
**Action:** RESEARCH

### 🟠 APT_ACTIVITY | Severity: HIGH
**Summary:** APT activity: 474b25badb40f524a7b2fe089e51eb7dbafd2e3e
**Description:** Linked to: UNC
**Source:** OTX/STIX
**Action:** RESEARCH

📭 No alerts ready for social media yet

## Alerts: 5 found | 2026-03-22T11:00:01.871004

### 🟠 APT_ACTIVITY | Severity: HIGH
**Summary:** APT activity: 4caa797130b5f7116f11c0b48013e430
**Description:** Linked to: UNC
**Source:** OTX/STIX
**Action:** RESEARCH

### 🟠 APT_ACTIVITY | Severity: HIGH
**Summary:** APT activity: 6272ef6ac1de8fb4bdd4a760be7ba5ed
**Description:** Linked to: UNC
**Source:** OTX/STIX
**Action:** RESEARCH

### 🟠 APT_ACTIVITY | Severity: HIGH
**Summary:** APT activity: c882d948d44a65019df54b0b2996677f
**Description:** Linked to: UNC
**Source:** OTX/STIX
**Action:** RESEARCH

### 🟠 APT_ACTIVITY | Severity: HIGH
**Summary:** APT activity: b6144f80b32b37393b2da565326cd5085c6842e1
**Description:** Linked to: UNC
**Source:** OTX/STIX
**Action:** RESEARCH

### 🟠 APT_ACTIVITY | Severity: HIGH
**Summary:** APT activity: 474b25badb40f524a7b2fe089e51eb7dbafd2e3e
**Description:** Linked to: UNC
**Source:** OTX/STIX
**Action:** RESEARCH

📭 No alerts ready for social media yet

## Alerts: 5 found | 2026-03-22T23:00:01.811264

### 🟠 APT_ACTIVITY | Severity: HIGH
**Summary:** APT activity: 4caa797130b5f7116f11c0b48013e430
**Description:** Linked to: UNC
**Source:** OTX/STIX
**Action:** RESEARCH

### 🟠 APT_ACTIVITY | Severity: HIGH
**Summary:** APT activity: 6272ef6ac1de8fb4bdd4a760be7ba5ed
**Description:** Linked to: UNC
**Source:** OTX/STIX
**Action:** RESEARCH

### 🟠 APT_ACTIVITY | Severity: HIGH
**Summary:** APT activity: c882d948d44a65019df54b0b2996677f
**Description:** Linked to: UNC
**Source:** OTX/STIX
**Action:** RESEARCH

### 🟠 APT_ACTIVITY | Severity: HIGH
**Summary:** APT activity: b6144f80b32b37393b2da565326cd5085c6842e1
**Description:** Linked to: UNC
**Source:** OTX/STIX
**Action:** RESEARCH

### 🟠 APT_ACTIVITY | Severity: HIGH
**Summary:** APT activity: 474b25badb40f524a7b2fe089e51eb7dbafd2e3e
**Description:** Linked to: UNC
**Source:** OTX/STIX
**Action:** RESEARCH

📭 No alerts ready for social media yet

## Alerts: 5 found | 2026-03-23T11:00:01.703610

### 🟠 APT_ACTIVITY | Severity: HIGH
**Summary:** APT activity: 4caa797130b5f7116f11c0b48013e430
**Description:** Linked to: UNC
**Source:** OTX/STIX
**Action:** RESEARCH

### 🟠 APT_ACTIVITY | Severity: HIGH
**Summary:** APT activity: 6272ef6ac1de8fb4bdd4a760be7ba5ed
**Description:** Linked to: UNC
**Source:** OTX/STIX
**Action:** RESEARCH

### 🟠 APT_ACTIVITY | Severity: HIGH
**Summary:** APT activity: c882d948d44a65019df54b0b2996677f
**Description:** Linked to: UNC
**Source:** OTX/STIX
**Action:** RESEARCH

### 🟠 APT_ACTIVITY | Severity: HIGH
**Summary:** APT activity: b6144f80b32b37393b2da565326cd5085c6842e1
**Description:** Linked to: UNC
**Source:** OTX/STIX
**Action:** RESEARCH

### 🟠 APT_ACTIVITY | Severity: HIGH
**Summary:** APT activity: 474b25badb40f524a7b2fe089e51eb7dbafd2e3e
**Description:** Linked to: UNC
**Source:** OTX/STIX
**Action:** RESEARCH

📭 No alerts ready for social media yet

## Alerts: 5 found | 2026-03-23T23:00:01.515254

### 🟠 APT_ACTIVITY | Severity: HIGH
**Summary:** APT activity: 4caa797130b5f7116f11c0b48013e430
**Description:** Linked to: UNC
**Source:** OTX/STIX
**Action:** RESEARCH

### 🟠 APT_ACTIVITY | Severity: HIGH
**Summary:** APT activity: 6272ef6ac1de8fb4bdd4a760be7ba5ed
**Description:** Linked to: UNC
**Source:** OTX/STIX
**Action:** RESEARCH

### 🟠 APT_ACTIVITY | Severity: HIGH
**Summary:** APT activity: c882d948d44a65019df54b0b2996677f
**Description:** Linked to: UNC
**Source:** OTX/STIX
**Action:** RESEARCH

### 🟠 APT_ACTIVITY | Severity: HIGH
**Summary:** APT activity: b6144f80b32b37393b2da565326cd5085c6842e1
**Description:** Linked to: UNC
**Source:** OTX/STIX
**Action:** RESEARCH

### 🟠 APT_ACTIVITY | Severity: HIGH
**Summary:** APT activity: 474b25badb40f524a7b2fe089e51eb7dbafd2e3e
**Description:** Linked to: UNC
**Source:** OTX/STIX
**Action:** RESEARCH

📭 No alerts ready for social media yet

## Alerts: 5 found | 2026-03-24T11:00:01.446443

### 🟠 APT_ACTIVITY | Severity: HIGH
**Summary:** APT activity: 4caa797130b5f7116f11c0b48013e430
**Description:** Linked to: UNC
**Source:** OTX/STIX
**Action:** RESEARCH

### 🟠 APT_ACTIVITY | Severity: HIGH
**Summary:** APT activity: 6272ef6ac1de8fb4bdd4a760be7ba5ed
**Description:** Linked to: UNC
**Source:** OTX/STIX
**Action:** RESEARCH

### 🟠 APT_ACTIVITY | Severity: HIGH
**Summary:** APT activity: c882d948d44a65019df54b0b2996677f
**Description:** Linked to: UNC
**Source:** OTX/STIX
**Action:** RESEARCH

### 🟠 APT_ACTIVITY | Severity: HIGH
**Summary:** APT activity: b6144f80b32b37393b2da565326cd5085c6842e1
**Description:** Linked to: UNC
**Source:** OTX/STIX
**Action:** RESEARCH

### 🟠 APT_ACTIVITY | Severity: HIGH
**Summary:** APT activity: 474b25badb40f524a7b2fe089e51eb7dbafd2e3e
**Description:** Linked to: UNC
**Source:** OTX/STIX
**Action:** RESEARCH

📭 No alerts ready for social media yet

## Alerts: 5 found | 2026-03-24T23:00:01.724283

### 🟠 APT_ACTIVITY | Severity: HIGH
**Summary:** APT activity: 4caa797130b5f7116f11c0b48013e430
**Description:** Linked to: UNC
**Source:** OTX/STIX
**Action:** RESEARCH

### 🟠 APT_ACTIVITY | Severity: HIGH
**Summary:** APT activity: 6272ef6ac1de8fb4bdd4a760be7ba5ed
**Description:** Linked to: UNC
**Source:** OTX/STIX
**Action:** RESEARCH

### 🟠 APT_ACTIVITY | Severity: HIGH
**Summary:** APT activity: c882d948d44a65019df54b0b2996677f
**Description:** Linked to: UNC
**Source:** OTX/STIX
**Action:** RESEARCH

### 🟠 APT_ACTIVITY | Severity: HIGH
**Summary:** APT activity: b6144f80b32b37393b2da565326cd5085c6842e1
**Description:** Linked to: UNC
**Source:** OTX/STIX
**Action:** RESEARCH

### 🟠 APT_ACTIVITY | Severity: HIGH
**Summary:** APT activity: 474b25badb40f524a7b2fe089e51eb7dbafd2e3e
**Description:** Linked to: UNC
**Source:** OTX/STIX
**Action:** RESEARCH

📭 No alerts ready for social media yet

## Alerts: 5 found | 2026-03-25T11:00:01.502357

### 🟠 APT_ACTIVITY | Severity: HIGH
**Summary:** APT activity: 4caa797130b5f7116f11c0b48013e430
**Description:** Linked to: UNC
**Source:** OTX/STIX
**Action:** RESEARCH

### 🟠 APT_ACTIVITY | Severity: HIGH
**Summary:** APT activity: 6272ef6ac1de8fb4bdd4a760be7ba5ed
**Description:** Linked to: UNC
**Source:** OTX/STIX
**Action:** RESEARCH

### 🟠 APT_ACTIVITY | Severity: HIGH
**Summary:** APT activity: c882d948d44a65019df54b0b2996677f
**Description:** Linked to: UNC
**Source:** OTX/STIX
**Action:** RESEARCH

### 🟠 APT_ACTIVITY | Severity: HIGH
**Summary:** APT activity: b6144f80b32b37393b2da565326cd5085c6842e1
**Description:** Linked to: UNC
**Source:** OTX/STIX
**Action:** RESEARCH

### 🟠 APT_ACTIVITY | Severity: HIGH
**Summary:** APT activity: 474b25badb40f524a7b2fe089e51eb7dbafd2e3e
**Description:** Linked to: UNC
**Source:** OTX/STIX
**Action:** RESEARCH

📭 No alerts ready for social media yet

## Alerts: 5 found | 2026-03-25T23:00:01.960984

### 🟠 APT_ACTIVITY | Severity: HIGH
**Summary:** APT activity: 4caa797130b5f7116f11c0b48013e430
**Description:** Linked to: UNC
**Source:** OTX/STIX
**Action:** RESEARCH

### 🟠 APT_ACTIVITY | Severity: HIGH
**Summary:** APT activity: 6272ef6ac1de8fb4bdd4a760be7ba5ed
**Description:** Linked to: UNC
**Source:** OTX/STIX
**Action:** RESEARCH

### 🟠 APT_ACTIVITY | Severity: HIGH
**Summary:** APT activity: c882d948d44a65019df54b0b2996677f
**Description:** Linked to: UNC
**Source:** OTX/STIX
**Action:** RESEARCH

### 🟠 APT_ACTIVITY | Severity: HIGH
**Summary:** APT activity: b6144f80b32b37393b2da565326cd5085c6842e1
**Description:** Linked to: UNC
**Source:** OTX/STIX
**Action:** RESEARCH

### 🟠 APT_ACTIVITY | Severity: HIGH
**Summary:** APT activity: 474b25badb40f524a7b2fe089e51eb7dbafd2e3e
**Description:** Linked to: UNC
**Source:** OTX/STIX
**Action:** RESEARCH

📭 No alerts ready for social media yet
No alerts triggered.
No alerts triggered.
No alerts triggered.
No alerts triggered.
No alerts triggered.
No alerts triggered.
No alerts triggered.
No alerts triggered.
No alerts triggered.
