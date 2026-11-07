import httpx
import pytest

from app.analyzers import llm

FINDING = {
    "tool": "bandit", "file": "a.py", "line": 3,
    "code": "B602", "severity": "high", "message": "shell=True is risky",
}
OK = {"candidates": [{"content": {"parts": [{"text": "Looks risky."}]}}]}


class FakeResponse:
    def __init__(self, status_code=200, data=None):
        self.status_code = status_code
        self._data = data or {}

    def json(self):
        return self._data


@pytest.fixture
def with_key(monkeypatch):
    monkeypatch.setattr(llm, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(llm.time, "sleep", lambda seconds: None)


def test_returns_none_without_key():
    assert llm.summarize({"a.py": "x = 1\n"}, []) is None


def test_returns_summary(with_key, monkeypatch):
    monkeypatch.setattr(llm.httpx, "post", lambda *a, **k: FakeResponse(200, OK))
    assert llm.summarize({"a.py": "x = 1\n"}, [FINDING]) == "Looks risky."


def test_retries_then_succeeds(with_key, monkeypatch):
    responses = [FakeResponse(429), FakeResponse(200, OK)]
    monkeypatch.setattr(llm.httpx, "post", lambda *a, **k: responses.pop(0))
    assert llm.summarize({"a.py": "x = 1\n"}, []) == "Looks risky."


def test_gives_up_immediately_on_client_error(with_key, monkeypatch):
    calls = []

    def post(*args, **kwargs):
        calls.append(1)
        return FakeResponse(401)

    monkeypatch.setattr(llm.httpx, "post", post)
    assert llm.summarize({"a.py": "x = 1\n"}, []) is None
    assert len(calls) == 1


def test_network_error_returns_none(with_key, monkeypatch):
    def boom(*args, **kwargs):
        raise httpx.ConnectError("down")

    monkeypatch.setattr(llm.httpx, "post", boom)
    assert llm.summarize({"a.py": "x = 1\n"}, []) is None


def test_blocked_response_returns_none(with_key, monkeypatch):
    monkeypatch.setattr(
        llm.httpx, "post", lambda *a, **k: FakeResponse(200, {"candidates": []})
    )
    assert llm.summarize({"a.py": "x = 1\n"}, []) is None


def test_prompt_truncates_big_files():
    prompt = llm.build_prompt({"big.py": "x" * 50_000}, [])
    assert len(prompt) < 20_000