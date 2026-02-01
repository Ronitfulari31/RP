import hashlib


def hash_text(text: str) -> str:
    if not text:
        return ""
    return hashlib.sha256(text.strip().lower().encode("utf-8")).hexdigest()


def hash_url(url: str) -> str:
    if not url:
        return ""
    return hashlib.sha256(url.strip().lower().encode("utf-8")).hexdigest()
