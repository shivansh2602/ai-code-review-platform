from app import models
from app.database import SessionLocal


def process_event(event_id: int, db=None) -> None:
    """Runs in the background worker. Day 3 will add the real analysis here."""
    owns_session = db is None
    db = db or SessionLocal()
    try:
        event = db.get(models.WebhookEvent, event_id)
        if event is None:
            return

        event.status = "processing"
        db.commit()

        db.add(models.Review(event_id=event.id, status="pending"))
        event.status = "done"
        db.commit()
    finally:
        if owns_session:
            db.close()