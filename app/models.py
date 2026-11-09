from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class WebhookEvent(Base):
    __tablename__ = "webhook_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    delivery_id: Mapped[str | None] = mapped_column(String(64))
    event_type: Mapped[str] = mapped_column(String(50), default="unknown")
    action: Mapped[str | None] = mapped_column(String(50))
    repo: Mapped[str | None] = mapped_column(String(200))
    pr_number: Mapped[int | None]
    payload: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(20), default="received")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )

    reviews: Mapped[list["Review"]] = relationship(back_populates="event")


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("webhook_events.id"))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    static_findings: Mapped[dict | None] = mapped_column(JSON)
    llm_summary: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )

    event: Mapped["WebhookEvent"] = relationship(back_populates="reviews")