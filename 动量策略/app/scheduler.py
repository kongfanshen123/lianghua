from datetime import date
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import logging
from app.pipeline import run_pipeline
from app.config import config

logger = logging.getLogger(__name__)


def start_scheduler():
    logger.info("Starting scheduler")

    scheduler = BackgroundScheduler(timezone="Asia/Shanghai")

    hour, minute = map(int, config.PIPELINE_TIME.split(":"))
    scheduler.add_job(
        run_pipeline,
        trigger=CronTrigger(hour=hour, minute=minute, day_of_week="mon-fri"),
        id="daily_pipeline",
        name="Daily momentum strategy pipeline",
        replace_existing=True,
    )

    scheduler.start()
    logger.info(f"Scheduler started with daily pipeline at {config.PIPELINE_TIME}")

    try:
        import time
        while True:
            time.sleep(3600)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Stopping scheduler")
        scheduler.shutdown()


def run_immediately():
    logger.info("Running pipeline immediately")
    result = run_pipeline(date.today())
    if result:
        logger.info("Pipeline completed successfully")
    else:
        logger.error("Pipeline failed")
    return result
