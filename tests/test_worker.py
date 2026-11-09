import httpx
import pytest

from app import models, worker


def make_event(db, pr_number=1):
    event = models.WebhookEvent(
        event_type="pull_request", repo="me/demo", pr_number=pr_number,
        payload={}, status="queued",
    )
    db.add(event)
    db.commit()
    return event


@pytest.fixture
def one_file(monkeypatch):
    monkeypatch.setattr(
        worker, "get_pr_python_files", lambda repo, pr: {"bad.py": "import os\n"}
    )


@pytest.fixture
def github(monkeypatch):
    """A fake GitHub comment API that records every call."""

    class Fake:
        def __init__(self):
            self.posted = []
            self.updated = []
            self.update_error = None

    fake = Fake()

    def post(repo, pr, body):
        fake.posted.append((repo, pr, body))
        return {"id": 100 + len(fake.posted)}

    def update(repo, comment_id, body):
        if fake.update_error:
            raise fake.update_error
        fake.updated.append((repo, comment_id, body))
        return {"id": comment_id}

    monkeypatch.setattr(worker, "post_pr_comment", post)
    monkeypatch.setattr(worker, "update_pr_comment", update)
    return fake


def test_worker_saves_findings_and_posts_comment(db_session, one_file, github):
    event = make_event(db_session)

    worker.process_event(event.id, db=db_session)

    db_session.refresh(event)
    review = db_session.query(models.Review).one()
    assert event.status == "done"
    assert review.status == "posted"
    assert any(f["code"] == "F401" for f in review.static_findings["findings"])
    assert len(github.posted) == 1
    assert github.posted[0][:2] == ("me/demo", 1)
    assert "F401" in github.posted[0][2]
    assert review.static_findings["comment_id"] == 101


def test_worker_marks_event_failed_when_fetch_fails(db_session, monkeypatch, github):
    def boom(repo, pr):
        raise RuntimeError("GitHub is down")

    monkeypatch.setattr(worker, "get_pr_python_files", boom)
    event = make_event(db_session)

    with pytest.raises(RuntimeError):
        worker.process_event(event.id, db=db_session)

    db_session.refresh(event)
    assert event.status == "failed"
    assert github.posted == []


def test_review_is_kept_when_posting_fails(db_session, one_file, monkeypatch):
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


def test_worker_includes_llm_summary(db_session, one_file, github, monkeypatch):
    monkeypatch.setattr(worker, "summarize", lambda files, findings: "Looks risky overall.")
    event = make_event(db_session)

    worker.process_event(event.id, db=db_session)

    review = db_session.query(models.Review).one()
    assert review.llm_summary == "Looks risky overall."
    assert "Looks risky overall." in github.posted[0][2]


def test_second_review_updates_existing_comment(db_session, one_file, github):
    worker.process_event(make_event(db_session).id, db=db_session)
    worker.process_event(make_event(db_session).id, db=db_session)

    assert len(github.posted) == 1
    assert len(github.updated) == 1
    assert github.updated[0][1] == 101


def test_new_comment_posted_if_old_one_was_deleted(db_session, one_file, github):
    worker.process_event(make_event(db_session).id, db=db_session)
    github.update_error = httpx.HTTPStatusError(
        "gone",
        request=httpx.Request("PATCH", "https://api.github.com/x"),
        response=httpx.Response(404),
    )

    worker.process_event(make_event(db_session).id, db=db_session)

    assert len(github.posted) == 2


def test_different_pr_gets_its_own_comment(db_session, one_file, github):
    worker.process_event(make_event(db_session, pr_number=1).id, db=db_session)
    worker.process_event(make_event(db_session, pr_number=2).id, db=db_session)

    assert len(github.posted) == 2
    assert github.updated == []


def test_worker_records_timings(db_session, one_file, github):
    event = make_event(db_session)

    worker.process_event(event.id, db=db_session)

    review = db_session.query(models.Review).one()
    assert set(review.static_findings["timings"]) == {"analysis_s", "llm_s", "total_s"}