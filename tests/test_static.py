from app.analyzers.static import analyze

BAD = (
    "import os\n"
    "import subprocess\n\n\n"
    "def run(cmd):\n"
    "    return subprocess.call(cmd, shell=True)\n\n\n"
    'password = "admin123"\n'
)


def test_finds_ruff_and_bandit_issues():
    findings = analyze({"bad.py": BAD})
    codes = {f["code"] for f in findings}
    assert {f["tool"] for f in findings} == {"ruff", "bandit"}
    assert "F401" in codes  # unused import
    assert "B602" in codes  # shell=True


def test_clean_code_has_no_findings():
    assert analyze({"ok.py": "x = 1\n"}) == []


def test_no_files():
    assert analyze({}) == []