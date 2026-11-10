import json
import subprocess
import sys
import tempfile
from pathlib import Path

RUFF_RULES = "E,F,B"


def _write_files(root: Path, files: dict[str, str]) -> None:
    root = root.resolve()
    for name, content in files.items():
        target = (root / name).resolve()
        if root not in target.parents:
            continue  # ignore any path that tries to escape the temp folder
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")


def _relative(path: str, root: Path) -> str:
    try:
        return Path(path).resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path


def run_ruff(root: Path) -> list[dict]:
    proc = subprocess.run(
        [
            sys.executable, "-m", "ruff", "check",
            "--isolated", "--no-cache",
            "--select", RUFF_RULES,
            "--output-format", "json",
            str(root),
        ],
        capture_output=True, text=True, timeout=60,
    )
    if proc.returncode not in (0, 1):
        raise RuntimeError(f"ruff failed: {proc.stderr}")
    return [
        {
            "tool": "ruff",
            "file": _relative(item["filename"], root),
            "line": item["location"]["row"],
            "code": item.get("code") or "syntax-error",
            "severity": "low",
            "message": item["message"],
        }
        for item in json.loads(proc.stdout or "[]")
    ]


def run_bandit(root: Path) -> list[dict]:
    proc = subprocess.run(
        [sys.executable, "-m", "bandit", "-r", str(root), "-f", "json", "-q"],
        capture_output=True, text=True, timeout=60,
    )
    if proc.returncode not in (0, 1):
        raise RuntimeError(f"bandit failed: {proc.stderr}")
    data = json.loads(proc.stdout or "{}")
    return [
        {
            "tool": "bandit",
            "file": _relative(item["filename"], root),
            "line": item["line_number"],
            "code": item["test_id"],
            "severity": item["issue_severity"].lower(),
            "message": item["issue_text"],
        }
        for item in data.get("results", [])
    ]


def analyze(files: dict[str, str]) -> list[dict]:
    """Runs Ruff and Bandit on {path: content} and returns one merged list."""
    if not files:
        return []
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write_files(root, files)
        findings = run_ruff(root) + run_bandit(root)
    return sorted(findings, key=lambda f: (f["file"], f["line"]))
