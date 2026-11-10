from app import models


def test_reviews_endpoint_lists_reviews(client, db_session):
    event = models.WebhookEvent(
        event_type="pull_request", repo="me/demo", pr_number=3,
        payload={}, status="done",
    )
    db_session.add(event)
    db_session.commit()
    db_session.add(
        models.Review(
            event_id=event.id,
            status="posted",
            static_findings={"findings": [{}, {}], "timings": {"total_s": 4.2}},
        )
    )
    db_session.commit()

    data = client.get("/reviews").json()

    assert data[0]["repo"] == "me/demo"
    assert data[0]["findings"] == 2
    assert data[0]["timings"]["total_s"] == 4.2
