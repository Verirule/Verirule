from app.worker.normalize import normalize


def test_normalize_html_strips_markup_to_visible_text() -> None:
    html = b"<html><body><h1>Policy</h1><script>ignore()</script><p>Line one</p></body></html>"
    result = normalize("text/html; charset=utf-8", html)

    assert result["normalized_text"] == "Policy\nLine one"
    assert result["text_preview"] == "Policy\nLine one"
    assert isinstance(result["text_fingerprint"], str)
    assert len(result["text_fingerprint"]) == 64
