"""Проверка ссылок и удаление рекламных параметров без сетевых запросов."""

import re
from urllib.parse import urlsplit


def normalize_url(value: str) -> str:
    value = value.strip()
    if value.startswith(("instagram.com/", "www.instagram.com/", "m.instagram.com/")):
        value = "https://" + value
    try:
        parts = urlsplit(value)
        valid_host = parts.hostname in {"instagram.com", "www.instagram.com", "m.instagram.com"}
        valid_port = parts.port in {None, 443}
    except ValueError as exc:
        raise ValueError("Некоректна адреса посилання.") from exc
    if (
        parts.scheme != "https" or not valid_host or not valid_port
        or parts.username is not None or parts.password is not None
    ):
        raise ValueError("Потрібне HTTPS-посилання на instagram.com/reel/…")
    match = re.fullmatch(r"/reels?/([A-Za-z0-9_-]+)/?", parts.path)
    if not match:
        raise ValueError("Потрібне посилання на окремий Reel: instagram.com/reel/КОД/")
    return f"https://www.instagram.com/reel/{match[1]}/"


def parse_urls(text: str) -> tuple[list[str], list[str]]:
    """Вернуть уникальные URL и ошибки; пустые строки и # комментарии пропускаются."""
    urls: list[str] = []
    errors: list[str] = []
    seen: set[str] = set()
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        for token in line.split():
            try:
                url = normalize_url(token)
            except ValueError as exc:
                errors.append(f"Рядок {number}: {exc}")
            else:
                if url not in seen:
                    urls.append(url)
                    seen.add(url)
    return urls, errors
