from apscheduler.schedulers.background import BackgroundScheduler

from logging_config import logger
from scout import generate_report

scheduler = BackgroundScheduler()


def scheduled_scout():
    logger.info("Scheduled Scout run triggered")

    try:
        report_path = generate_report()
        logger.info(f"Scheduled Scout run completed: {report_path}")
    except Exception as e:
        logger.exception(f"Scheduled Scout run failed: {e}")
        raise


def start_scheduler():
    if scheduler.running:
        logger.info("Scheduler already running")
        return

    logger.info("Registering scheduled Scout job")

    scheduler.add_job(
        scheduled_scout,
        trigger="cron",
        hour=8,
        minute=0,
        id="scheduled_scout",
        replace_existing=True,
    )

    scheduler.start()

    logger.info("Scout scheduler started")