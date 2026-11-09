MARKER = "<!-- ai-review-bot -->"
MAX_ROWS = 20
SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def _cell(text) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def format_comment(files: list[str], findings: list[dict], summary: str | None = None) -> str:
    lines = [MARKER, "## Automated code review", ""]

    if summary:
        lines += ["### AI summary", "", summary, ""]

    if not files:
        lines.append("No Python files were changed in this PR, so there was nothing to analyze.")
        return "\n".join(lines)

    lines.append(
        f"Analyzed {len(files)} Python file(s): " + ", ".join(f"`{f}`" for f in files)
    )
    lines.append("")

    if not findings:
        lines.append("No issues found by Ruff or Bandit.")
        return "\n".join(lines)

    ordered = sorted(
        findings,
        key=lambda f: (SEVERITY_ORDER.get(f["severity"], 3), f["file"], f["line"]),
    )
    counts = {level: sum(1 for f in findings if f["severity"] == level) for level in SEVERITY_ORDER}
    lines.append(
        f"**{len(findings)} finding(s):** {counts['high']} high, "
        f"{counts['medium']} medium, {counts['low']} low"
    )

    unparsed = sorted(
        {f["file"] for f in findings if f["code"] in ("invalid-syntax", "syntax-error")}
    )
    if unparsed:
        names = ", ".join(f"`{name}`" for name in unparsed)
        lines += [
            "",
            f"**Warning:** could not parse {names} (syntax error). "
            "Security analysis was skipped for these files.",
        ]



    lines += ["", "| Severity | Location | Rule | Issue |", "|---|---|---|---|"]

    for f in ordered[:MAX_ROWS]:
        lines.append(
            f"| {f['severity']} | `{_cell(f['file'])}:{f['line']}` | "
            f"{f['tool']} {_cell(f['code'])} | {_cell(f['message'])} |"
        )

    hidden = len(ordered) - MAX_ROWS
    if hidden > 0:
        lines += ["", f"...and {hidden} more not shown."]

    return "\n".join(lines)