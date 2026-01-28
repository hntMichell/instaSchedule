import os
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
from publisher import publish_post

scheduler = BackgroundScheduler()

def start_scheduler(debug=False):
    if scheduler.running:
        return
    if debug and os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        return
    scheduler.start()

def schedule_post(post_id, data):
    start_scheduler()
    run_date = datetime.fromisoformat(data["scheduled_at"])
    scheduler.add_job(
        publish_post,
        "date",
        run_date=run_date,
        args=[post_id],
        id=f"post_{post_id}",
        replace_existing=True
    )

def cancel_post(post_id):
    start_scheduler()
    try:
        scheduler.remove_job(f"post_{post_id}")
    except Exception:
        pass
