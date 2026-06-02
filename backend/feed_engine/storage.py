from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

from feed_engine.errors import FeedEngineError

T = TypeVar("T", bound=Callable[..., Any])


def require_db_function(name: str) -> T:
    import db

    value = getattr(db, name, None)
    if value is None:
        raise FeedEngineError(
            "STORAGE_UNAVAILABLE",
            "Storage API is not available yet.",
            status_code=503,
            context={"missing": name, "expected_module": "backend/db"},
        )
    return value

