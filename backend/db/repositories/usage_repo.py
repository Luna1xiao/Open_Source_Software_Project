from pathlib import Path

from app.schemas.usage import UsageBucket
from db.connection import connection


def record_usage(
    day: str,
    provider: str,
    model: str,
    agent: str,
    prompt_tokens: int,
    completion_tokens: int,
    db_path: Path | str | None = None,
    failed: bool = False,
) -> None:
    """Add one LLM usage event into the daily provider/model/agent bucket."""
    with connection(db_path) as conn:
        with conn:
            conn.execute(
                """
                INSERT INTO usage_buckets (
                    day,
                    provider,
                    model,
                    agent,
                    prompt_tokens,
                    completion_tokens,
                    requests,
                    failures
                )
                VALUES (?, ?, ?, ?, ?, ?, 1, ?)
                ON CONFLICT(day, provider, model, agent) DO UPDATE SET
                    prompt_tokens = prompt_tokens + excluded.prompt_tokens,
                    completion_tokens = completion_tokens + excluded.completion_tokens,
                    requests = requests + 1,
                    failures = failures + excluded.failures
                """,
                (
                    day,
                    provider,
                    model,
                    agent,
                    prompt_tokens,
                    completion_tokens,
                    int(failed),
                ),
            )


def query_usage(
    start_day: str | None = None,
    end_day: str | None = None,
    provider: str | None = None,
    model: str | None = None,
    agent: str | None = None,
    db_path: Path | str | None = None,
) -> list[UsageBucket]:
    """Query daily LLM usage buckets for reporting charts."""
    sql = "SELECT * FROM usage_buckets"
    clauses: list[str] = []
    params: list[str] = []

    if start_day is not None:
        clauses.append("day >= ?")
        params.append(start_day)
    if end_day is not None:
        clauses.append("day <= ?")
        params.append(end_day)
    if provider is not None:
        clauses.append("provider = ?")
        params.append(provider)
    if model is not None:
        clauses.append("model = ?")
        params.append(model)
    if agent is not None:
        clauses.append("agent = ?")
        params.append(agent)

    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY day ASC"

    with connection(db_path) as conn:
        rows = conn.execute(sql, params).fetchall()

    return [
        UsageBucket(
            day=row["day"],
            prompt_tokens=row["prompt_tokens"],
            completion_tokens=row["completion_tokens"],
            requests=row["requests"],
            failures=row["failures"],
        )
        for row in rows
    ]
