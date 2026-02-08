import hashlib


def hash_raw_text(raw_text: str) -> str:
    """Return SHA256 hash for a regulation raw_text."""
    return hashlib.sha256(raw_text.encode("utf-8")).hexdigest()


def has_content_changed(new_hash: str, latest_hash: str | None) -> bool:
    """Return True when content hash is new or changed."""
    return latest_hash != new_hash
