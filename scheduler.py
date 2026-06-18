from apscheduler.schedulers.background import BackgroundScheduler
from scout import generate_report

scheduler = BackgroundScheduler()

def scheduled_scout():
    print("Running scheduled Scout...")
    generate_report()

def start_scheduler():

    scheduler.add_job(
        scheduled_scout,
        trigger="cron",
        hour=8,
        minute=0
    )

    scheduler.start()

    print("Scout scheduler started.")