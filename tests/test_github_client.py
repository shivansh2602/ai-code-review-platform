from app import github_client


class FakeResponse:
    text = "x = 1\n"

    def raise_for_status(self):
        pass


def test_file_paths_are_url_encoded(monkeypatch):
    seen = {}

    def fake_get(url, **kwargs):
        seen["url"] = url
        return FakeResponse()

    monkeypatch.setattr(github_client.httpx, "get", fake_get)

    github_client.get_file_content("o/r", "src/a#b?.py", "abc")

    assert seen["url"].endswith("/contents/src/a%23b%3F.py")
