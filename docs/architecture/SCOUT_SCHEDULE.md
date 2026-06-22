# Scout Schedule

> Cadence specification and "schedule position" definition.
> Derives from `SCOUT_CHARTER.md`. Last verified against commit: fdf0ab8

## 1. Current Schedule (as-built, Phase D2)

| Job | Trigger | Time | Default | Source |
|-----|---------|------|---------|--------|
| `scheduled_audit` | APScheduler cron | `SCOUT_AUDIT_HOUR:MINUTE` `SCOUT_AUDIT_TZ` (default **08:00 America/New_York**) | enabled (`SCOUT_AUDIT_ENABLED=true`) | `scheduler.py` |
| `scheduled_scout` (legacy) | APScheduler cron | 08:00 server-local | **disabled** (`SCOUT_LEGACY_JOB_ENABLED=false`) | `scheduler.py` |

The daily **dataset-audit** job runs `run_dataset_audit()` — producing all reports including
the Daily Digest (`reports/digest/daily_digest.md`) and appending an `audit_history`
snapshot. It makes **no LLM calls** (free/safe to run daily). Job callbacks never re-raise,
so a failed run is logged without stopping the scheduler; `coalesce=True` +
`misfire_grace_time` collapse missed windows (no catch-up storm); `max_instances=1` prevents
overlap. The in-process scheduler requires a **single worker** (cross-process memory unsafe;
SQLite deferred). The dashboard's hardcoded "08:00 UTC" label is stale (dashboard work is out
of scope here).

### 1.1 Running manually / externally

- **CLI:** `python scout_audit.py` (exit 0 success / 1 failure) — same execution path.
- **HTTP:** `POST /run-audit`.
- **Robust VM option** (systemd timer calling the CLI; set `SCOUT_AUDIT_ENABLED=false` for
  the web process to avoid double-firing):

```ini
# /etc/systemd/system/scout-audit.service
[Service]
Type=oneshot
WorkingDirectory=/opt/edenseek-scout
Environment=SCOUT_DATASET_DIR=/path/to/dataset
ExecStart=/opt/edenseek-scout/venv/bin/python scout_audit.py

# /etc/systemd/system/scout-audit.timer
[Timer]
OnCalendar=*-*-* 08:00:00
[Install]
WantedBy=timers.target
```

## 2. Target Schedule (v0.4+)

| Job               | Cadence                                                | Purpose |
|-------------------|--------------------------------------------------------|---------|
| Strategic Report  | daily 08:00                                            | Standing intelligence report |
| Intake Report     | on demand (session start) + optional daily pre-report  | Continuity briefing |
| Memory Maintenance| after each report                                      | Extraction / dedup |

All times should be defined in a single config with an explicit timezone. Recommended:
store schedule as data, expose via a scheduler-status endpoint, render dashboard from it.

## 3. Schedule Position (definition)

"Schedule Position" is a field in the Intake Report answering *where are we in the
cadence?* It is computed read-only:

```json
{
  "last_run": "<timestamp of most recent report>",
  "last_run_type": "strategic | intake",
  "next_scheduled": "<next cron firing>",
  "runs_today": 0,
  "cadence": "daily 08:00 (server local)"
}
```

## 4. Constraints

- No durable job store yet — schedule is reconstructed each startup (Charter §5 reliability
  applies: a missed window is logged, never silently retried into a billing storm).
- Manual triggers must be rate-limited before unattended exposure widens.
