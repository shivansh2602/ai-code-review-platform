from app import models
from app.analyzers.static import analyze
from app.database import SessionLocal
from app.github_client import get_pr_python_files


def process_event(event_id: int, db=None) -> None:
    """Runs in the background worker."""
    owns_session = db is None
    db = db or SessionLocal()
    try:
        event = db.get(models.WebhookEvent, event_id)
        if event is None:
            return

        event.status = "processing"
        db.commit()

        try:
            if not event.repo or event.pr_number is None:
                raise ValueError("Event has no repo or PR number")
            files = get_pr_python_files(event.repo, event.pr_number)
            findings = analyze(files)
        except Exception:
            event.status = "failed"
            db.commit()
            raise  # re-raise so RQ also records the job as failed

        db.add(
            models.Review(
                event_id=event.id,
                status="analyzed",
                static_findings={"files_analyzed": sorted(files), "findings": findings},
            )
        )
        event.status = "done"
        db.commit()
    finally:
        if owns_session:
            db.close()