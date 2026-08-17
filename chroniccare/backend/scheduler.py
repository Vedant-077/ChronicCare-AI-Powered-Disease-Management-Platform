# scheduler.py
# This is the "background task scheduler" -- a job that runs on its own,
# on a timer, independent of any user clicking anything.
#
# Every minute, it:
#   1. Gets the current time as "HH:MM"
#   2. Looks at every medicine in the database
#   3. If a medicine's reminder time matches right now, AND we haven't
#      already notified for this exact minute, it creates a Notification row.
#
# The frontend then polls GET /notifications every so often to display them.
# This is the same fundamental idea as Celery + Redis (a worker doing
# scheduled work outside the request/response cycle) but needs no separate
# broker process to install -- APScheduler runs inside the same Python process
# as the API. For a larger production system with multiple servers, Celery +
# Redis (or similar) is the standard next step, since it can distribute jobs
# across many worker machines.

from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler

from database import SessionLocal
import models

scheduler = BackgroundScheduler()


def check_medicine_reminders():
    db = SessionLocal()
    try:
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        current_minute_key = now.strftime("%Y-%m-%d %H:%M")

        medicines = db.query(models.Medicine).all()
        for med in medicines:
            scheduled_times = [t.strip() for t in med.times.split(",") if t.strip()]
            if current_time not in scheduled_times:
                continue

            # Avoid creating a duplicate notification for the same minute
            already_sent = (
                db.query(models.Notification)
                .filter(
                    models.Notification.medicine_id == med.id,
                    models.Notification.message.like(f"%{current_minute_key}%"),
                )
                .first()
            )
            if already_sent:
                continue

            notification = models.Notification(
                user_id=med.user_id,
                medicine_id=med.id,
                message=f"Time to take {med.name}"
                + (f" ({med.dosage})" if med.dosage else "")
                + f" -- scheduled {current_minute_key}",
            )
            db.add(notification)

        db.commit()
    finally:
        db.close()


def start_scheduler():
    # Runs check_medicine_reminders() every 60 seconds, forever, in the background.
    scheduler.add_job(check_medicine_reminders, "interval", seconds=60, id="medicine_reminder_check")
    scheduler.start()
