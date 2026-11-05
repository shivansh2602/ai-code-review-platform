import pytest

from app import models, worker


def make_event(db):
    event = models.WebhookEvent(
        event_type="pull_request", repo="me/demo", pr_number=1,
        payload={}, status="queued",
    )
    db.add(event)
    db.commit()
    return event


def test_worker_saves_static_findings(db_session, monkeypatch):
    monkeypatch.setattr(
        worker, "get_pr_python_files", lambda repo, pr: {"bad.py": "import os\n"}
    )
    event = make_event(db_session)

    worker.process_event(event.id, db=db_session)

    db_session.refresh(event)
    review = db_session.query(models.Review).one()
    assert event.status == "done"
    assert review.status == "analyzed"
    assert any(f["code"] == "F401" for f in review.static_findings["findings"])


def test_worker_marks_event_failed_on_error(db_session, monkeypatch):
    def boom(repo, pr):
        raise RuntimeError("GitHub is down")

    monkeypatch.setattr(worker, "get_pr_python_files", boom)
    event = make_event(db_session)

    with pytest.raises(RuntimeError):
        worker.process_event(event.id, db=db_session)

    db_session.refresh(event)
    assert event.status == "failed"