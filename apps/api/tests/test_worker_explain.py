from app.worker.explain import build_explanation


def test_build_explanation_limits_diff_preview_size() -> None:
    previous = "\n".join([f"line {idx}" for idx in range(300)])
    current = "\n".join([f"line {idx} changed" for idx in range(300)])

    result = build_explanation(previous, current)
    preview = result["diff_preview"] or ""

    assert isinstance(result["summary"], str)
    assert result["summary"]
    assert isinstance(result["citations"], list)
    assert len(result["citations"]) <= 3
    assert len(preview.splitlines()) <= 201
