import hashlib
import hmac
import json

import pytest
from fastapi.testclient import TestClient

from app import main

SECRET = "test-secret"
BODY = json.dumps({"hello": "world"}).encode()

client = TestClient(main.app)


def sign(body: bytes, secret: str) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


@pytest.fixture(autouse=True)
def use_test_secret(monkeypatch):
    monkeypatch.setattr(main, "WEBHOOK_SECRET", SECRET)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_valid_signature_accepted():
    headers = {"X-Hub-Signature-256": sign(BODY, SECRET)}
    response = client.post("/webhook", content=BODY, headers=headers)
    assert response.status_code == 200


def test_wrong_secret_rejected():
    headers = {"X-Hub-Signature-256": sign(BODY, "wrong-secret")}
    response = client.post("/webhook", content=BODY, headers=headers)
    assert response.status_code == 401


def test_missing_signature_rejected():
    response = client.post("/webhook", content=BODY)
    assert response.status_code == 401