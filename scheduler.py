from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
from publisher import publish_post

scheduler = BackgroundScheduler()
scheduler.start()

def schedule_post(post_id, data):
    run_date = datetime.fromisoformat(data["scheduled_at"])
    scheduler.add_job(
        publish_post,
        "date",
        run_date=run_date,
        args=[post_id]
    )
