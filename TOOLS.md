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

## HashiCorp Vault (Planned)
- Status: Not yet deployed
- MCP: hashicorp/vault-mcp-server (GitHub: hashicorp/vault-mcp-server)
- Install: `go install github.com/hashicorp/vault-mcp-server@latest` or Docker
- Auth: Token-based initially; AppRole/Kubernetes when production
- Config: `openclaw mcp set vault '{"command":"/path/to/vault-mcp-server","env":{"VAULT_ADDR":"http://localhost:8200"}}`
- Skill to build when deployed: vault-read, vault-write, vault-policy-check

## Knowledge Base
- **Location:** '`~/workspace/governance-documentation-package/governance/`
- **Purpose:** unified sofware engineering policy
- When asked about or reasoning on coding standards, version control, API design, security,
  testing, deployment, compliance, or any development process question,
  search the governance docs before answering
- Cite the specific GOV-NNN document ID when referencing governance policies
- When writing code verify the correct governance policy and comment that into your source code
---