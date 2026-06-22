"""APScheduler wiring (Phase D2 automation).

Registers the daily dataset-audit job (which produces all reports incl. the
Daily Digest and appends an audit-history snapshot). The legacy strategic-report
job is kept but disabled by default. The scheduler is in-process; deploy with a
single worker (cross-process safety is deferred). Job callbacks never re-raise,
so a failed run is logged without killing the scheduler.
"""
import os

from apscheduler.schedulers.background import BackgroundScheduler

from logging_config import logger
import dataset_auditor
from scout import generate_report

scheduler = BackgroundScheduler()


def _flag(name, default):
    return os.getenv(name, default).strip().lower() == "true"


def _audit_enabled():
    return _flag("SCOUT_AUDIT_ENABLED", "true")


def _legacy_enabled():
    return _flag("SCOUT_LEGACY_JOB_ENABLED", "false")


def _audit_cron():
    return {
        "hour": int(os.getenv("SCOUT_AUDIT_HOUR", "8")),
        "minute": int(os.getenv("SCOUT_AUDIT_MINUTE", "0")),
        "timezone": os.getenv("SCOUT_AUDIT_TZ", "America/New_York"),
    }


def scheduled_audit():
    """Run the daily dataset audit. Logs failures; never re-raises (keeps scheduler alive)."""
    logger.info("Scheduled dataset audit triggered")
    try:
        result = dataset_auditor.run_dataset_audit()
        logger.info(
            f"Scheduled dataset audit completed: quality_score={result['quality_score']}, "
            f"reports={len(result['reports'])}"
        )
    except Exception as e:
        logger.exception(f"Scheduled dataset audit failed: {e}")


def scheduled_scout():
    """Legacy strategic-report job (OpenAI). Disabled by default. Never re-raises."""
    logger.info("Scheduled Scout (legacy) run triggered")
    try:
        report_path = generate_report()
        logger.info(f"Scheduled Scout (legacy) run completed: {report_path}")
    except Exception as e:
        logger.exception(f"Scheduled Scout (legacy) run failed: {e}")


def register_jobs(sched):
    """Register jobs on ``sched`` per env flags. Returns the registered job ids."""
    registered = []

    if _audit_enabled():
        cron = _audit_cron()
        sched.add_job(
            scheduled_audit,
            trigger="cron",
            hour=cron["hour"],
            minute=cron["minute"],
            timezone=cron["timezone"],
            id="scheduled_audit",
            replace_existing=True,
            coalesce=True,           # collapse missed runs into one
            max_instances=1,         # never overlap audits
            misfire_grace_time=3600,
        )
        registered.append("scheduled_audit")
        logger.info(f"Registered daily dataset-audit job at "
                    f"{cron['hour']:02d}:{cron['minute']:02d} {cron['timezone']}")
    else:
        logger.info("Dataset-audit job disabled (SCOUT_AUDIT_ENABLED=false)")

    if _legacy_enabled():
        sched.add_job(
            scheduled_scout,
            trigger="cron",
            hour=8,
            minute=0,
            id="scheduled_scout",
            replace_existing=True,
        )
        registered.append("scheduled_scout")
        logger.info("Registered legacy strategic-report job")

    return registered


def start_scheduler():
    if scheduler.running:
        logger.info("Scheduler already running")
        return

    register_jobs(scheduler)
    scheduler.start()
    logger.info("Scout scheduler started")
