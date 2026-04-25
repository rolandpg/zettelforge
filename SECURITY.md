# Security Policy

## Reporting a Vulnerability

This is a solo-maintainer project. For security-related issues:
- Open a GitHub Security Advisory in the repository
- Tag with `security` label
- Expect acknowledgement within 48 hours

## Supported Versions

| Version | Supported |
|---------|-----------|
| latest release | ✅ |
| master branch | ✅ (CI gates) |
| older releases | ❌ |

## Supply Chain Security

This project implements:
- SHA-pinned GitHub Actions (all third-party actions pinned by commit SHA)
- PyPI trusted publishing (OIDC, no long-lived tokens)
- pip-audit on every CI run (HIGH/CRITICAL must pass)
- Dependabot for weekly dependency updates
- Snyk SAST scanning on every push/PR
