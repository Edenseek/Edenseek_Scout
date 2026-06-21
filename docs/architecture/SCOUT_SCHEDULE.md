# Scout Schedule

> Cadence specification and "schedule position" definition.
> Derives from `SCOUT_CHARTER.md`. Last verified against commit: fdf0ab8

## 1. Current Schedule (as-built)

| Job              | Trigger          | Time               | Source |
|------------------|------------------|--------------------|--------|
| scheduled_scout  | APScheduler cron | 08:00 server-local | `scheduler.py` |

Note: the dashboard label reads "08:00 UTC" but the cron fires in **server local time**.
This mismatch is a known drift item to resolve (display from live scheduler state).

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
