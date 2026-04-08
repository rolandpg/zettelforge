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
No alerts triggered.
No alerts triggered.

## Alerts: 1 found | 2026-03-31T23:00:01.259752

### 🔴 CRITICAL_CVE | Severity: CRITICAL
**Summary:** CVE-CVE-2026-3055 - CVSS 9.0
**Description:** Citrix NetScaler ADC (formerly Citrix ADC), NetScaler Gateway (formerly Citrix Gateway) and NetScaler ADC FIPS and NDcPP contain an out-of-bounds reads vulnerability when configured as a SAML IDP lead
**Source:** NVD
**Action:** RESEARCH

📭 No alerts ready for social media yet

## Alerts: 1 found | 2026-04-01T11:00:01.851189

### 🔴 CRITICAL_CVE | Severity: CRITICAL
**Summary:** CVE-CVE-2026-3055 - CVSS 9.0
**Description:** Citrix NetScaler ADC (formerly Citrix ADC), NetScaler Gateway (formerly Citrix Gateway) and NetScaler ADC FIPS and NDcPP contain an out-of-bounds reads vulnerability when configured as a SAML IDP lead
**Source:** NVD
**Action:** RESEARCH

📭 No alerts ready for social media yet

## Alerts: 1 found | 2026-04-01T23:00:01.720677

### 🔴 CRITICAL_CVE | Severity: CRITICAL
**Summary:** CVE-CVE-2026-3055 - CVSS 9.0
**Description:** Citrix NetScaler ADC (formerly Citrix ADC), NetScaler Gateway (formerly Citrix Gateway) and NetScaler ADC FIPS and NDcPP contain an out-of-bounds reads vulnerability when configured as a SAML IDP lead
**Source:** NVD
**Action:** RESEARCH

📭 No alerts ready for social media yet

## Alerts: 1 found | 2026-04-02T11:00:01.595249

### 🔴 CRITICAL_CVE | Severity: CRITICAL
**Summary:** CVE-CVE-2026-3055 - CVSS 9.0
**Description:** Citrix NetScaler ADC (formerly Citrix ADC), NetScaler Gateway (formerly Citrix Gateway) and NetScaler ADC FIPS and NDcPP contain an out-of-bounds reads vulnerability when configured as a SAML IDP lead
**Source:** NVD
**Action:** RESEARCH

📭 No alerts ready for social media yet

## Alerts: 1 found | 2026-04-02T23:00:01.461658

### 🔴 CRITICAL_CVE | Severity: CRITICAL
**Summary:** CVE-CVE-2026-3055 - CVSS 9.0
**Description:** Citrix NetScaler ADC (formerly Citrix ADC), NetScaler Gateway (formerly Citrix Gateway) and NetScaler ADC FIPS and NDcPP contain an out-of-bounds reads vulnerability when configured as a SAML IDP lead
**Source:** NVD
**Action:** RESEARCH

📭 No alerts ready for social media yet

## Alerts: 1 found | 2026-04-03T11:00:01.179433

### 🔴 CRITICAL_CVE | Severity: CRITICAL
**Summary:** CVE-CVE-2026-3055 - CVSS 9.0
**Description:** Citrix NetScaler ADC (formerly Citrix ADC), NetScaler Gateway (formerly Citrix Gateway) and NetScaler ADC FIPS and NDcPP contain an out-of-bounds reads vulnerability when configured as a SAML IDP lead
**Source:** NVD
**Action:** RESEARCH

📭 No alerts ready for social media yet

## Alerts: 1 found | 2026-04-03T23:00:01.586912

### 🔴 CRITICAL_CVE | Severity: CRITICAL
**Summary:** CVE-CVE-2026-3055 - CVSS 9.0
**Description:** Citrix NetScaler ADC (formerly Citrix ADC), NetScaler Gateway (formerly Citrix Gateway) and NetScaler ADC FIPS and NDcPP contain an out-of-bounds reads vulnerability when configured as a SAML IDP lead
**Source:** NVD
**Action:** RESEARCH

📭 No alerts ready for social media yet

## Alerts: 1 found | 2026-04-04T11:00:01.659085

### 🔴 CRITICAL_CVE | Severity: CRITICAL
**Summary:** CVE-CVE-2026-3055 - CVSS 9.0
**Description:** Citrix NetScaler ADC (formerly Citrix ADC), NetScaler Gateway (formerly Citrix Gateway) and NetScaler ADC FIPS and NDcPP contain an out-of-bounds reads vulnerability when configured as a SAML IDP lead
**Source:** NVD
**Action:** RESEARCH

📭 No alerts ready for social media yet

## Alerts: 1 found | 2026-04-04T23:00:01.307511

### 🔴 CRITICAL_CVE | Severity: CRITICAL
**Summary:** CVE-CVE-2026-3055 - CVSS 9.0
**Description:** Citrix NetScaler ADC (formerly Citrix ADC), NetScaler Gateway (formerly Citrix Gateway) and NetScaler ADC FIPS and NDcPP contain an out-of-bounds reads vulnerability when configured as a SAML IDP lead
**Source:** NVD
**Action:** RESEARCH

📭 No alerts ready for social media yet

## Alerts: 1 found | 2026-04-05T11:00:01.837003

### 🔴 CRITICAL_CVE | Severity: CRITICAL
**Summary:** CVE-CVE-2026-3055 - CVSS 9.0
**Description:** Citrix NetScaler ADC (formerly Citrix ADC), NetScaler Gateway (formerly Citrix Gateway) and NetScaler ADC FIPS and NDcPP contain an out-of-bounds reads vulnerability when configured as a SAML IDP lead
**Source:** NVD
**Action:** RESEARCH

📭 No alerts ready for social media yet

## Alerts: 1 found | 2026-04-05T23:00:01.180665

### 🔴 CRITICAL_CVE | Severity: CRITICAL
**Summary:** CVE-CVE-2026-3055 - CVSS 9.0
**Description:** Citrix NetScaler ADC (formerly Citrix ADC), NetScaler Gateway (formerly Citrix Gateway) and NetScaler ADC FIPS and NDcPP contain an out-of-bounds reads vulnerability when configured as a SAML IDP lead
**Source:** NVD
**Action:** RESEARCH

📭 No alerts ready for social media yet

## Alerts: 1 found | 2026-04-06T11:00:02.034618

### 🔴 CRITICAL_CVE | Severity: CRITICAL
**Summary:** CVE-CVE-2026-3055 - CVSS 9.0
**Description:** Citrix NetScaler ADC (formerly Citrix ADC), NetScaler Gateway (formerly Citrix Gateway) and NetScaler ADC FIPS and NDcPP contain an out-of-bounds reads vulnerability when configured as a SAML IDP lead
**Source:** NVD
**Action:** RESEARCH

📭 No alerts ready for social media yet

## Alerts: 2 found | 2026-04-06T23:00:01.303092

### 🔴 CRITICAL_CVE | Severity: CRITICAL
**Summary:** CVE-CVE-2026-3055 - CVSS 9.0
**Description:** Citrix NetScaler ADC (formerly Citrix ADC), NetScaler Gateway (formerly Citrix Gateway) and NetScaler ADC FIPS and NDcPP contain an out-of-bounds reads vulnerability when configured as a SAML IDP lead
**Source:** NVD
**Action:** RESEARCH

### 🔴 CRITICAL_CVE | Severity: CRITICAL
**Summary:** CVE-CVE-2026-35616 - CVSS 9.0
**Description:** Fortinet FortiClient EMS contains an improper access control vulnerability that may allow an unauthenticated attacker to execute unauthorized code or commands via crafted requests.
**Source:** NVD
**Action:** RESEARCH

📭 No alerts ready for social media yet
python3: can't open file '/home/rolandpg/cti-workspace/manage.py': [Errno 2] No such file or directory
Traceback (most recent call last):
  File "/home/rolandpg/cti-workspace/manage.py", line 6, in <module>
    execute_from_command_line(sys.argv)
  File "/home/rolandpg/.local/lib/python3.12/site-packages/django/core/management/__init__.py", line 443, in execute_from_command_line
    utility.execute()
  File "/home/rolandpg/.local/lib/python3.12/site-packages/django/core/management/__init__.py", line 417, in execute
    django.setup()
  File "/home/rolandpg/.local/lib/python3.12/site-packages/django/__init__.py", line 24, in setup
    apps.populate(settings.INSTALLED_APPS)
  File "/home/rolandpg/.local/lib/python3.12/site-packages/django/apps/registry.py", line 116, in populate
    app_config.import_models()
  File "/home/rolandpg/.local/lib/python3.12/site-packages/django/apps/config.py", line 269, in import_models
    self.models_module = import_module(models_module_name)
                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/lib/python3.12/importlib/__init__.py", line 90, in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "<frozen importlib._bootstrap>", line 1387, in _gcd_import
  File "<frozen importlib._bootstrap>", line 1360, in _find_and_load
  File "<frozen importlib._bootstrap>", line 1331, in _find_and_load_unlocked
  File "<frozen importlib._bootstrap>", line 935, in _load_unlocked
  File "<frozen importlib._bootstrap_external>", line 995, in exec_module
  File "<frozen importlib._bootstrap>", line 488, in _call_with_frames_removed
  File "/home/rolandpg/cti-workspace/intel/models.py", line 4, in <module>
    _module = SourcelessFileLoader('intel_models_pyc', str(_pyc)).load_module()
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "<frozen importlib._bootstrap_external>", line 649, in _check_name_wrapper
  File "<frozen importlib._bootstrap_external>", line 1176, in load_module
  File "<frozen importlib._bootstrap_external>", line 1000, in load_module
  File "<frozen importlib._bootstrap>", line 537, in _load_module_shim
  File "<frozen importlib._bootstrap>", line 966, in _load
  File "<frozen importlib._bootstrap>", line 935, in _load_unlocked
  File "<frozen importlib._bootstrap_external>", line 995, in exec_module
  File "<frozen importlib._bootstrap>", line 488, in _call_with_frames_removed
  File "/home/rolandpg/cti-workspace/intel/models.py", line 4, in <module>
    _module = SourcelessFileLoader('intel_models_pyc', str(_pyc)).load_module()
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "<frozen importlib._bootstrap_external>", line 649, in _check_name_wrapper
  File "<frozen importlib._bootstrap_external>", line 1176, in load_module
  File "<frozen importlib._bootstrap_external>", line 1000, in load_module
  File "<frozen importlib._bootstrap>", line 534, in _load_module_shim
  File "<frozen importlib._bootstrap>", line 866, in _exec
  File "<frozen importlib._bootstrap_external>", line 991, in exec_module
  File "<frozen importlib._bootstrap_external>", line 1249, in get_code
  File "<frozen importlib._bootstrap_external>", line 1189, in get_data
FileNotFoundError: [Errno 2] No such file or directory: '/home/rolandpg/cti-workspace/intel/__pycache__/__pycache__/models.cpython-312.pyc'
