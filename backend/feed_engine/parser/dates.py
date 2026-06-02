from __future__ import annotations

from datetime import UTC, datetime
from email.utils import parsedate_to_datetime


def parse_date(value: str | None) -> str:
    if not value:
        return ""

    text = value.strip()
    if not text:
        return ""

    parsed: datetime | None = None
    try:
        parsed = parsedate_to_datetime(text)
    except (TypeError, ValueError):
        normalized = text.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError:
            return ""

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC).isoformat().replace("+00:00", "Z")

