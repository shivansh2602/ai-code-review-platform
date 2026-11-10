from urllib.parse import quote

import httpx

from app.config import GITHUB_TOKEN

API = "https://api.github.com"
MAX_FILES = 50
MAX_FILE_BYTES = 200_000


def _headers(accept: str = "application/vnd.github+json") -> dict:
    headers = {"Accept": accept, "X-GitHub-Api-Version": "2022-11-28"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return headers


def get_pr(repo: str, pr_number: int) -> dict:
    response = httpx.get(
        f"{API}/repos/{repo}/pulls/{pr_number}", headers=_headers(), timeout=30
    )
    response.raise_for_status()
    return response.json()


def get_changed_files(repo: str, pr_number: int) -> list[dict]:
    response = httpx.get(
        f"{API}/repos/{repo}/pulls/{pr_number}/files",
        params={"per_page": 100},
        headers=_headers(),
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def get_file_content(repo: str, path: str, ref: str) -> str:
    response = httpx.get(
        f"{API}/repos/{repo}/contents/{quote(path, safe='/')}",
        params={"ref": ref},
        headers=_headers("application/vnd.github.raw+json"),
        timeout=30,
    )
    response.raise_for_status()
    return response.text


def get_pr_python_files(repo: str, pr_number: int) -> dict[str, str]:
    """Returns {file path: file content} for the .py files changed in the PR."""
    head_sha = get_pr(repo, pr_number)["head"]["sha"]
    files: dict[str, str] = {}
    for changed in get_changed_files(repo, pr_number):
        name = changed["filename"]
        if changed["status"] == "removed" or not name.endswith(".py"):
            continue
        if len(files) >= MAX_FILES:
            break
        content = get_file_content(repo, name, head_sha)
        if len(content.encode()) <= MAX_FILE_BYTES:
            files[name] = content
    return files


def post_pr_comment(repo: str, pr_number: int, body: str) -> dict:
    # GitHub treats PR conversation comments as "issue comments".
    response = httpx.post(
        f"{API}/repos/{repo}/issues/{pr_number}/comments",
        json={"body": body},
        headers=_headers(),
        timeout=30,
    )
    response.raise_for_status()
    return response.json()



def update_pr_comment(repo: str, comment_id: int, body: str) -> dict:
    response = httpx.patch(
        f"{API}/repos/{repo}/issues/comments/{comment_id}",
        json={"body": body},
        headers=_headers(),
        timeout=30,
    )
    response.raise_for_status()
    return response.json()
