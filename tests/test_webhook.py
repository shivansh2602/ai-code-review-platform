import hashlib
import hmac
import json

from app import models

SECRET = "test-secret"
BODY = json.dumps(
    {"action": "opened", "number": 7, "repository": {"full_name": "me/demo"}}
).encode()


def sign(body: bytes, secret: str) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_valid_signature_accepted(client):
    headers = {"X-Hub-Signature-256": sign(BODY, SECRET)}
    response = client.post("/webhook", content=BODY, headers=headers)
    assert response.status_code == 200
    assert response.json()["message"] == "received"


def test_wrong_secret_rejected(client):
    headers = {"X-Hub-Signature-256": sign(BODY, "wrong-secret")}
    response = client.post("/webhook", content=BODY, headers=headers)
    assert response.status_code == 401


def test_missing_signature_rejected(client):
    response = client.post("/webhook", content=BODY)
    assert response.status_code == 401


def test_event_is_saved_to_database(client, db_session):
    headers = {
        "X-Hub-Signature-256": sign(BODY, SECRET),
        "X-GitHub-Event": "pull_request",
    }
    client.post("/webhook", content=BODY, headers=headers)

    events = db_session.query(models.WebhookEvent).all()
    assert len(events) == 1
    assert events[0].repo == "me/demo"
    assert events[0].pr_number == 7
    assert events[0].event_type == "pull_request"


def test_invalid_json_rejected(client):
    bad_body = b"not json"
    headers = {"X-Hub-Signature-256": sign(bad_body, SECRET)}
    response = client.post("/webhook", content=bad_body, headers=headers)
    assert response.status_code == 400