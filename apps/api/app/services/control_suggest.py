from __future__ import annotations

import re
from typing import Any

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokens(value: str) -> set[str]:
    return set(_TOKEN_RE.findall(value.lower()))


def _normalize_tag(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")


def _extract_tags(value: Any) -> set[str]:
    if not isinstance(value, list):
        return set()
    tags: set[str] = set()
    for item in value:
        if isinstance(item, str):
            normalized = _normalize_tag(item)
            if normalized:
                tags.add(normalized)
    return tags


def suggest_controls_for_finding(
    finding: dict[str, Any],
    explanation: dict[str, Any] | None,
    template_tags: list[str],
    control_catalog: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    explanation_payload = explanation if isinstance(explanation, dict) else {}
    finding_tags = _extract_tags(finding.get("tags"))
    source_tags = _extract_tags(template_tags)
    search_tags = finding_tags | source_tags

    text_parts = [
        str(finding.get("title") or ""),
        str(finding.get("summary") or ""),
        str(explanation_payload.get("summary") or ""),
        str(explanation_payload.get("diff_preview") or ""),
    ]
    text_tokens = _tokens(" ".join(text_parts))

    ranked: list[dict[str, Any]] = []
    for control in control_catalog:
        control_id = control.get("id")
        framework_slug = control.get("framework_slug")
        control_key = control.get("control_key")
        title = control.get("title")
        if not all(isinstance(field, str) and field for field in (control_id, framework_slug, control_key, title)):
            continue

        control_tags = _extract_tags(control.get("tags"))
        overlapping_tags = sorted(search_tags & control_tags)
        tag_score = len(overlapping_tags) * 4

        control_text = " ".join(
            [
                str(control_key),
                str(title),
                str(control.get("description") or ""),
                " ".join(sorted(control_tags)),
            ]
        )
        control_tokens = _tokens(control_text)
        overlapping_tokens = sorted(text_tokens & control_tokens)
        keyword_score = min(len(overlapping_tokens), 6)

        score = tag_score + keyword_score
        if score <= 0:
            continue

        if score >= 9:
            confidence = "high"
        elif score >= 4:
            confidence = "medium"
        else:
            confidence = "low"

        reasons: list[str] = []
        if overlapping_tags:
            reasons.append(f"Matched tags: {', '.join(overlapping_tags[:4])}")
        if overlapping_tokens:
            reasons.append(f"Matched keywords: {', '.join(overlapping_tokens[:5])}")

        ranked.append(
            {
                "control_id": control_id,
                "framework_slug": framework_slug,
                "control_key": control_key,
                "title": title,
                "confidence": confidence,
                "score": score,
                "reasons": reasons,
            }
        )

    ranked.sort(
        key=lambda item: (
            -int(item["score"]),
            str(item["framework_slug"]),
            str(item["control_key"]),
            str(item["control_id"]),
        )
    )
    return ranked[:5]

