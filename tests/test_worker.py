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


@pytest.fixture
def posted(monkeypatch):
    calls = []
    monkeypatch.setattr(
        worker, "post_pr_comment", lambda repo, pr, body: calls.append((repo, pr, body))
    )
    return calls


def test_worker_saves_findings_and_posts_comment(db_session, monkeypatch, posted):
    monkeypatch.setattr(
        worker, "get_pr_python_files", lambda repo, pr: {"bad.py": "import os\n"}
    )
    event = make_event(db_session)

    worker.process_event(event.id, db=db_session)

    db_session.refresh(event)
    review = db_session.query(models.Review).one()
    assert event.status == "done"
    assert review.status == "posted"
    assert any(f["code"] == "F401" for f in review.static_findings["findings"])
    assert len(posted) == 1
    assert posted[0][0] == "me/demo" and posted[0][1] == 1
    assert "F401" in posted[0][2]


def test_worker_marks_event_failed_when_fetch_fails(db_session, monkeypatch, posted):
    def boom(repo, pr):
        raise RuntimeError("GitHub is down")

    monkeypatch.setattr(worker, "get_pr_python_files", boom)
    event = make_event(db_session)

    with pytest.raises(RuntimeError):
        worker.process_event(event.id, db=db_session)

    db_session.refresh(event)
    assert event.status == "failed"
    assert posted == []


def test_review_is_kept_when_posting_fails(db_session, monkeypatch):
    monkeypatch.setattr(worker, "get_pr_python_files", lambda repo, pr: {"ok.py": "x = 1\n"})

    def refuse(repo, pr, body):
        raise RuntimeError("403 Forbidden")

    monkeypatch.setattr(worker, "post_pr_comment", refuse)
    event = make_event(db_session)

    with pytest.raises(RuntimeError):
        worker.process_event(event.id, db=db_session)

    db_session.refresh(event)
    review = db_session.query(models.Review).one()
    assert event.status == "failed"
    assert review.status == "analyzed"