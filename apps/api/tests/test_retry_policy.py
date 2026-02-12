from app.worker.retry import backoff_seconds, sanitize_error


def test_backoff_seconds_schedule() -> None:
    assert backoff_seconds(1) == 60
    assert backoff_seconds(2) == 300
    assert backoff_seconds(3) == 900
    assert backoff_seconds(4) == 3600
    assert backoff_seconds(5) == 21600
    assert backoff_seconds(6) == 21600


def test_sanitize_error_redacts_sensitive_values() -> None:
    exc = ValueError("Authorization: Bearer secret-token-abc")
    error_text = sanitize_error(exc, default_message="failed")
    assert "secret-token-abc" not in error_text
    assert "[redacted]" in error_text
