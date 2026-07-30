"""APScheduler wiring (Phase D2 automation).

Registers the daily dataset-audit job (which produces all reports incl. the
Daily Digest and appends an audit-history snapshot). The legacy strategic-report,
delta-audit reconciliation, and Registry-rebuild jobs are kept but disabled by
default (opt-in via env flags); the latter two orchestrate the certified pipelines
and change no audit/Registry/Discovery behavior. The scheduler is in-process; deploy
with a single worker (cross-process safety is deferred). Job callbacks never re-raise,
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


def _delta_reconcile_enabled():
    # OFF by default — the production VM scheduler is NOT activated in this increment.
    return _flag("SCOUT_DELTA_RECONCILE_ENABLED", "false")


def _reconcile_interval_minutes():
    try:
        m = int(os.getenv("SCOUT_RECONCILE_INTERVAL_MINUTES", "15"))
    except ValueError:
        m = 15
    return m if m > 0 else 15


def _registry_rebuild_enabled():
    # OFF by default — orchestration is not activated on the production VM in this increment.
    return _flag("SCOUT_REGISTRY_REBUILD_ENABLED", "false")


def _registry_rebuild_interval_minutes():
    try:
        m = int(os.getenv("SCOUT_REGISTRY_REBUILD_INTERVAL_MINUTES", "60"))
    except ValueError:
        m = 60
    return m if m > 0 else 60


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


def scheduled_delta_reconcile():
    """Reconciliation trigger for the synchronization/delta audit — the SAME canonical agent entry
    point as the event-watch and manual triggers. Idempotent + ledger-guarded. Never re-raises."""
    logger.info("Scheduled delta-audit reconciliation triggered")
    try:
        import scout_delta_audit  # lazy import (keeps scheduler import light)
        result = scout_delta_audit.audit_current_revision(trigger="reconciliation")
        logger.info(f"Delta-audit reconciliation: {result.get('status')} "
                    f"(revision {result.get('revision_id')})")
    except Exception as e:
        logger.exception(f"Delta-audit reconciliation failed: {e}")


def scheduled_registry_rebuild():
    """Rebuild the derived Registry from authoritative Publisher data via Discovery -> the certified
    resolve/persist pipeline (``scout_registry.rebuild_discovered``). **Orchestration only** — it changes
    no Registry or Discovery behavior. Idempotent (a rebuildable projection). Never re-raises."""
    logger.info("Scheduled Registry rebuild triggered")
    try:
        import scout_registry  # lazy import (keeps scheduler import light)
        result = scout_registry.rebuild_discovered()
        logger.info(f"Registry rebuild: {result.get('discovered')} issue(s) discovered, "
                    f"{result.get('count')} in Registry")
    except Exception as e:
        logger.exception(f"Scheduled Registry rebuild failed: {e}")


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

    # Delta-audit reconciliation (configurable interval). OFF by default — NOT activated on the
    # production VM in this increment. When enabled it calls the same canonical agent entry point.
    if _delta_reconcile_enabled():
        minutes = _reconcile_interval_minutes()
        sched.add_job(
            scheduled_delta_reconcile,
            trigger="interval",
            minutes=minutes,
            id="scheduled_delta_reconcile",
            replace_existing=True,
            coalesce=True,
            max_instances=1,
            misfire_grace_time=600,
        )
        registered.append("scheduled_delta_reconcile")
        logger.info(f"Registered delta-audit reconciliation job (every {minutes} min)")
    else:
        logger.info("Delta-audit reconciliation job disabled (SCOUT_DELTA_RECONCILE_ENABLED=false)")

    # Registry rebuild (Discovery -> certified rebuild). OFF by default — orchestration only; it changes
    # no Registry/Discovery behavior. When enabled it calls the certified publisher-wide rebuild.
    if _registry_rebuild_enabled():
        minutes = _registry_rebuild_interval_minutes()
        sched.add_job(
            scheduled_registry_rebuild,
            trigger="interval",
            minutes=minutes,
            id="scheduled_registry_rebuild",
            replace_existing=True,
            coalesce=True,
            max_instances=1,
            misfire_grace_time=900,
        )
        registered.append("scheduled_registry_rebuild")
        logger.info(f"Registered Registry rebuild job (every {minutes} min)")
    else:
        logger.info("Registry rebuild job disabled (SCOUT_REGISTRY_REBUILD_ENABLED=false)")

    return registered


def start_scheduler():
    if scheduler.running:
        logger.info("Scheduler already running")
        return

    register_jobs(scheduler)
    scheduler.start()
    logger.info("Scout scheduler started")
