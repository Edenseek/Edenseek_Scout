"""Scout revision watcher — the automated trigger for the deterministic audit.

This is the **trigger layer**, kept deliberately separate from the deterministic
audit pipeline (``dataset_auditor.run_dataset_audit``). It polls the mutable
Publisher pointer ``approved/published.json``, compares the current Approved
Dataset revision against the revision Scout last reported, and runs the existing
audit + report publication **only when the revision has changed**. Because the
trigger is decoupled, polling can later be replaced by an event-driven source
(EventBridge/SQS/S3 notifications) that calls ``check_and_audit`` unchanged — the
audit logic never moves.

Governance / behavior:
  * Read-only on the Publisher Repository; the audit writes only to the Scout
    Repository (``edenseek-scout``). No Publisher writes are introduced.
  * **No LLM at any point.** On an unchanged revision the watcher performs only the
    pointer read, the revision comparison, a log line, and a clean exit. The audit
    itself is deterministic and LLM-free.
  * **Idempotent** — it publishes only when the current revision differs from the
    revision recorded in the latest persisted Scout Report, so repeated polls on the
    same revision are no-ops (no duplicate history snapshots).
  * **Fail-loud** — a single check surfaces S3/config errors (CLI exit 1). The
    optional ``--loop`` mode logs a failed cycle and continues to the next tick.

Usage:
    python scout_watch.py           # one poll cycle, then exit (systemd timer / cron / EventBridge)
    python scout_watch.py --loop    # poll every SCOUT_WATCH_INTERVAL_SECONDS (local development)
Exit code 0 on success (whether unchanged or published), 1 on failure.
"""
import os
import sys
import time

from logging_config import logger
import audit_s3_source
import scout_report_publisher
import dataset_auditor

# Polling cadence is configuration, never hard-coded: local dev may poll every
# minute, production every 5–10 minutes. Read from the environment; the invoking
# scheduler (systemd timer / cron) sets the real cadence for single-shot runs.
WATCH_INTERVAL_ENV = "SCOUT_WATCH_INTERVAL_SECONDS"
DEFAULT_INTERVAL_SECONDS = 300


def check_and_audit():
    """Run one poll cycle: audit + publish iff the Approved Dataset revision changed.

    Pointer read + comparison only when unchanged (no materialization, no LLM).
    Returns a status dict; raises on any S3/config error (fail-loud).
    """
    current = audit_s3_source.resolve_current_revision()
    current_rev = current["revision_id"]
    last_rev = scout_report_publisher.last_published_revision_id()

    if current_rev == last_rev:
        logger.info(f"Scout watch: revision unchanged ({current_rev}); no audit.")
        return {"status": "unchanged", "revision_id": current_rev}

    logger.info(
        f"Scout watch: new Approved Dataset revision detected "
        f"({last_rev or 'none'} -> {current_rev}); running deterministic audit."
    )
    result = dataset_auditor.run_dataset_audit()
    logger.info(
        f"Scout watch: audit published for revision {current_rev} "
        f"(quality_score={result.get('quality_score')})."
    )
    return {"status": "published", "revision_id": current_rev, "audit": result}


def _interval_seconds():
    raw = os.getenv(WATCH_INTERVAL_ENV)
    if not raw:
        return DEFAULT_INTERVAL_SECONDS
    try:
        value = int(raw)
    except ValueError:
        logger.warning(
            f"Scout watch: invalid {WATCH_INTERVAL_ENV}={raw!r}; "
            f"using {DEFAULT_INTERVAL_SECONDS}s."
        )
        return DEFAULT_INTERVAL_SECONDS
    return value if value > 0 else DEFAULT_INTERVAL_SECONDS


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    if "--loop" not in argv:
        # Single-shot: for the systemd timer / cron / future event source.
        try:
            check_and_audit()
            return 0
        except Exception as e:
            logger.exception(f"Scout watch: check failed: {e}")
            return 1

    # Loop mode (local development). Resilient: a failed cycle is logged and the
    # watcher continues to the next tick rather than exiting.
    interval = _interval_seconds()
    logger.info(f"Scout watch: loop mode, polling every {interval}s.")
    while True:
        try:
            check_and_audit()
        except Exception as e:
            logger.exception(f"Scout watch: cycle failed (continuing): {e}")
        time.sleep(interval)


if __name__ == "__main__":
    sys.exit(main())
