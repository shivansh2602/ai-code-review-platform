import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import main, models  # noqa: F401
from app.analyzers import llm
from app.database import Base, get_db


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False)()
    yield session
    session.close()
    engine.dispose()


@pytest.fixture
def enqueued(monkeypatch):
    """Replaces the real Redis queue with a simple list we can inspect."""
    calls = []
    monkeypatch.setattr(main, "enqueue_event", calls.append)
    return calls


@pytest.fixture
def client(db_session, enqueued, monkeypatch):
    monkeypatch.setattr(main, "WEBHOOK_SECRET", "test-secret")

    def override_get_db():
        yield db_session

    main.app.dependency_overrides[get_db] = override_get_db
    yield TestClient(main.app)
    main.app.dependency_overrides.clear()

@pytest.fixture(autouse=True)
def no_real_llm(monkeypatch):
    """Tests never call the real Gemini API, whatever is in .env."""
    monkeypatch.setattr(llm, "GEMINI_API_KEY", "")
