# TOOLS.md - Local Notes

## X.com (xurl) — PRE-AUTHENTICATED, USE IMMEDIATELY
- **Command:** `xurl post "text"` — works without any auth setup
- **Path:** `~/.npm-global/lib/node_modules/@xdevplatform/xurl/cli.js`
- **Account:** @Deuslogica (Patrick Roland)
- **Verified working 2026-03-20** — posted APT28 thread successfully
- **REMEMBER: Already authenticated. Do NOT search for auth instructions.**

## CTI Stack
- **CTI Graph DB:** `~/cti-workspace/data/cti/cti.db`
- **DarkWeb Observatory:** `~/cti-workspace/darkweb-observatory/`
- **Dashboard:** `~/cti-workspace/darkweb-observatory/output/html/index.html`
- **Scripts:** `~/cti-workspace/collect_*.py`
- **Logs:** `~/cti-workspace/data/cti/*.log`

## Tor
- **Test Tor:** `curl -x socks5h://localhost:9050 https://check.torproject.org/api/ip`
- **Socks5 syntax:** `-x socks5h://` (not `--socks5h`)

## Systemd Timers
- **Location:** `~/.config/systemd/user/`
- **Timers:** `openclaw-memory-daily.timer`, `openclaw-memory-weekly.timer`
- **Note:** Service files must be copied here, not symlinked

## Django CTI Database
- **Workspace:** `~/cti-workspace/`
- **Settings:** `DJANGO_SETTINGS_MODULE=ctidb.settings`
- **Models:** `IOC`, `ThreatActor`, `CVE`, `Sector`, `ThreatAlert`
- **Check fields:** `python3 manage.py shell -c "from intel.models import Model; print([f.name for f in Model._meta.get_fields()])"`

## HashiCorp Vault — ACTIVE
- **Status:** Deployed and operational (2026-04-04)
- **Container:** `vault-dev` (Docker, auto-restart)
- **Address:** `http://127.0.0.1:8200`
- **Root token:** `patton-vault-dev-root` (homelab only, never use in prod)
- **KV Engine:** `secret/` (KV v2)
- **Auth:** AppRole enabled
- **Credentials:** `~/.openclaw/vault-credentials/{agent}.json`
- **Policies:** per-agent least-privilege (`patton`, `tamara`, `vigil`, `nexus`)
- **CLI helper:** `python3 scripts/vault_helper.py [read|write|list|auth-check]`
- **Setup script:** `scripts/vault-setup.sh`
- **Skills:** `skills/vault-read/SKILL.md`, `skills/vault-write/SKILL.md`, `skills/vault-setup/SKILL.md`
- **Onboarding:** `fleet/vault_agent_onboarding.md`
- **Next:** MCP server (hashicorp/vault-mcp-server) for direct tool integration

## Knowledge Base
- **Location:** '`~/workspace/governance-documentation-package/governance/`
- **Purpose:** unified sofware engineering policy
- When asked about or reasoning on coding standards, version control, API design, security,
  testing, deployment, compliance, or any development process question,
  search the governance docs before answering
- Cite the specific GOV-NNN document ID when referencing governance policies
- When writing code verify the correct governance policy and comment that into your source code
---