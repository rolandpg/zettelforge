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
