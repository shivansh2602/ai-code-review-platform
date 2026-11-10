from app.review_format import MARKER, format_comment

FINDING = {
    "tool": "bandit", "file": "a.py", "line": 3,
    "code": "B602", "severity": "high", "message": "shell=True is risky",
}


def test_comment_lists_findings():
    body = format_comment(["a.py"], [FINDING])
    assert MARKER in body
    assert "B602" in body
    assert "1 high" in body


def test_no_findings():
    assert "No issues found" in format_comment(["a.py"], [])


def test_no_files():
    assert "nothing to analyze" in format_comment([], [])


def test_long_lists_are_truncated():
    findings = [dict(FINDING, line=i) for i in range(30)]
    assert "and 10 more" in format_comment(["a.py"], findings)


def test_pipes_in_messages_do_not_break_the_table():
    body = format_comment(["a.py"], [dict(FINDING, message="a | b")])
    assert "a \\| b" in body

def test_summary_is_included():
    body = format_comment(["a.py"], [FINDING], summary="Short summary")
    assert "Short summary" in body

def test_syntax_errors_are_called_out():
    broken = dict(
        FINDING, tool="ruff", code="invalid-syntax", severity="low",
        message="Unexpected indentation",
    )
    assert "could not parse" in format_comment(["a.py"], [broken])
