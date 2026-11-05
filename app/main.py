import hashlib
import hmac
import json
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app import models
from app.config import WEBHOOK_SECRET
from app.database import Base, engine, get_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(lifespan=lifespan)


def verify_signature(body: bytes, signature_header: str | None) -> bool:
    if not WEBHOOK_SECRET or not signature_header:
        return False
    expected = "sha256=" + hmac.new(
        WEBHOOK_SECRET.encode(), body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature_header)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/webhook")
async def webhook(
    request: Request,
    x_hub_signature_256: str | None = Header(default=None),
    x_github_event: str = Header(default="unknown"),
    x_github_delivery: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    body = await request.body()

    if not verify_signature(body, x_hub_signature_256):
        raise HTTPException(status_code=401, detail="Invalid signature")

    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Body is not valid JSON")

    event = models.WebhookEvent(
        delivery_id=x_github_delivery,
        event_type=x_github_event,
        action=data.get("action"),
        repo=(data.get("repository") or {}).get("full_name"),
        pr_number=data.get("number"),
        payload=data,
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    return {"message": "received", "event_id": event.id}