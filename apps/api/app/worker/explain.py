from __future__ import annotations

import difflib
from typing import Any


def _truncate(value: str, limit: int = 280) -> str:
    if len(value) <= limit:
        return value
    return f"{value[: limit - 3]}..."


def build_explanation(prev_text: str, new_text: str) -> dict[str, Any]:
    previous = (prev_text or "").strip()
    current = (new_text or "").strip()
    if not previous or not current:
        return {
            "summary": "Content changed. A detailed text diff is unavailable for this source format.",
            "diff_preview": None,
            "citations": [],
        }

    diff_lines = list(
        difflib.unified_diff(
            previous.splitlines(),
            current.splitlines(),
            fromfile="previous",
            tofile="current",
            n=2,
            lineterm="",
        )
    )

    max_lines = 200
    preview_lines = diff_lines[:max_lines]
    if len(diff_lines) > max_lines:
        preview_lines.append("... diff truncated ...")
    diff_preview = "\n".join(preview_lines)

    citations: list[dict[str, str]] = []
    current_hunk = ""
    for line in diff_lines:
        if line.startswith("@@"):
            current_hunk = line
            continue
        if line.startswith(("+++", "---")):
            continue
        if line.startswith(("+", "-")):
            quote = _truncate(line[1:].strip())
            if quote:
                citations.append(
                    {
                        "quote": quote,
                        "context": current_hunk or "content update",
                    }
                )
            if len(citations) >= 3:
                break

    change_sections = sum(1 for line in diff_lines if line.startswith("@@"))
    citation_count = len(citations)
    summary = (
        f"The source updated {change_sections or 1} section(s) since the previous capture. "
        f"{citation_count} notable line-level change(s) are highlighted for review. "
        "See the diff preview for exact additions and removals."
    )

    return {
        "summary": summary,
        "diff_preview": diff_preview,
        "citations": citations,
    }
