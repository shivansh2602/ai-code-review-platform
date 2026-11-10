import time

import httpx

from app import models
from app.analyzers.llm import summarize
from app.analyzers.static import analyze
from app.database import SessionLocal
from app.github_client import (
    get_pr_python_files,
    post_pr_comment,
    update_pr_comment,
)
from app.review_format import format_comment


def find_previous_comment_id(db, repo: str, pr_number: int) -> int | None:
    """Looks up the bot's earlier comment on this PR, if there is one."""
    rows = (
        db.query(models.Review)
        .join(models.WebhookEvent, models.Review.event_id == models.WebhookEvent.id)
        .filter(models.WebhookEvent.repo == repo, models.WebhookEvent.pr_number == pr_number)
        .order_by(models.Review.id.desc())
        .limit(20)
        .all()
    )
    for row in rows:
        comment_id = (row.static_findings or {}).get("comment_id")
        if comment_id:
            return comment_id
    return None


def publish_comment(db, event, body: str) -> int:
    """Edits the bot's earlier comment, or posts a new one. Returns the comment id."""
    previous = find_previous_comment_id(db, event.repo, event.pr_number)
    if previous:
        try:
            return update_pr_comment(event.repo, previous, body)["id"]
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code != 404:
                raise
            # The old comment was deleted by someone, so post a fresh one.
    return post_pr_comment(event.repo, event.pr_number, body)["id"]


def process_event(event_id: int, db=None) -> None:
    """Runs in the background worker."""
    owns_session = db is None
    db = db or SessionLocal()
    try:
        event = db.get(models.WebhookEvent, event_id)
        if event is None:
            return

        started = time.perf_counter()
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
        analysis_s = time.perf_counter() - started

        llm_started = time.perf_counter()
        summary = summarize(files, findings)  # returns None on any problem
        llm_s = time.perf_counter() - llm_started

        # Save the analysis first, so it is kept even if posting fails.
        details = {"files_analyzed": sorted(files), "findings": findings}
        review = models.Review(
            event_id=event.id,
            status="analyzed",
            static_findings=details,
            llm_summary=summary,
        )
        db.add(review)
        db.commit()

        try:
            comment_id = publish_comment(
                db, event, format_comment(sorted(files), findings, summary)
            )
        except Exception:
            event.status = "failed"
            db.commit()
            raise

        review.static_findings = {
            **details,
            "comment_id": comment_id,
            "timings": {
                "analysis_s": round(analysis_s, 2),
                "llm_s": round(llm_s, 2),
                "total_s": round(time.perf_counter() - started, 2),
            },
        }
        review.status = "posted"
        event.status = "done"
        db.commit()
    finally:
        if owns_session:
            db.close()
