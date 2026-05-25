import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

from app.schemas.agent import SummaryResult, TranslationResult
from db.connection import connection

VALID_AGENT_STATUSES = {"idle", "queued", "running", "success", "failure", "cancelled"}


def start_agent_run(
    article_id: str,
    agent_type: str,
    provider: str,
    model: str,
    db_path: Path | str | None = None,
    target_lang: str | None = None,
    input_hash: str | None = None,
) -> str:
    """Create a durable agent run record and return its generated run id."""
    run_id = str(uuid.uuid4())
    with connection(db_path) as conn:
        with conn:
            conn.execute(
                """
                INSERT INTO agent_runs (
                    id,
                    article_id,
                    agent_type,
                    status,
                    provider,
                    model,
                    input_hash,
                    target_lang
                )
                VALUES (?, ?, ?, 'running', ?, ?, ?, ?)
                """,
                (run_id, article_id, agent_type, provider, model, input_hash, target_lang),
            )
    return run_id


def append_agent_step(
    run_id: str,
    name: str,
    status: str,
    input_json: dict | None = None,
    output_json: dict | None = None,
    db_path: Path | str | None = None,
    error_message: str | None = None,
) -> str:
    """Append one ordered trace step to an agent run."""
    step_id = str(uuid.uuid4())
    with connection(db_path) as conn:
        with conn:
            next_index = conn.execute(
                "SELECT COALESCE(MAX(step_index), -1) + 1 FROM agent_steps WHERE run_id = ?",
                (run_id,),
            ).fetchone()[0]
            conn.execute(
                """
                INSERT INTO agent_steps (
                    id,
                    run_id,
                    step_index,
                    name,
                    status,
                    input_json,
                    output_json,
                    error_message,
                    finished_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    step_id,
                    run_id,
                    next_index,
                    name,
                    status,
                    json.dumps(input_json or {}),
                    json.dumps(output_json or {}),
                    error_message,
                    _utc_now() if status in {"success", "failure"} else None,
                ),
            )
    return step_id


def finish_agent_run(
    run_id: str,
    status: str,
    db_path: Path | str | None = None,
    output_text: str | None = None,
    output_json: dict | None = None,
    error_message: str | None = None,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
) -> None:
    """Mark an agent run finished and persist output, errors, and token usage."""
    _validate_agent_status(status)
    with connection(db_path) as conn:
        with conn:
            conn.execute(
                """
                UPDATE agent_runs
                SET status = ?,
                    output_text = ?,
                    output_json = ?,
                    error_message = ?,
                    prompt_tokens = ?,
                    completion_tokens = ?,
                    total_tokens = ?,
                    finished_at = ?
                WHERE id = ?
                """,
                (
                    status,
                    output_text,
                    json.dumps(output_json or {}),
                    error_message,
                    prompt_tokens,
                    completion_tokens,
                    prompt_tokens + completion_tokens,
                    _utc_now(),
                    run_id,
                ),
            )


def save_agent_result(
    result: SummaryResult | TranslationResult,
    db_path: Path | str | None = None,
) -> str:
    """Persist a SummaryResult or TranslationResult as a completed agent run."""
    agent_type = "translation" if isinstance(result, TranslationResult) else "summary"
    target_lang = result.target_lang if isinstance(result, TranslationResult) else None
    output_text = (
        result.translation_html if isinstance(result, TranslationResult) else result.summary_text
    )
    run_id = start_agent_run(
        article_id=result.entry_id,
        agent_type=agent_type,
        provider=result.provider,
        model=result.model,
        target_lang=target_lang,
        db_path=db_path,
    )
    finish_agent_run(
        run_id,
        status=result.status,
        output_text=output_text,
        output_json=result.model_dump(),
        db_path=db_path,
    )
    return run_id


def get_latest_agent_result(
    article_id: str,
    agent_type: str,
    db_path: Path | str | None = None,
    target_lang: str | None = None,
) -> dict | None:
    """Return the latest successful agent run for an article and agent type."""
    sql = """
        SELECT *
        FROM agent_runs
        WHERE article_id = ?
            AND agent_type = ?
            AND status = 'success'
    """
    params: list[str] = [article_id, agent_type]
    if target_lang is not None:
        sql += " AND target_lang = ?"
        params.append(target_lang)
    sql += " ORDER BY finished_at DESC, started_at DESC LIMIT 1"

    with connection(db_path) as conn:
        row = conn.execute(sql, params).fetchone()

    if row is None:
        return None
    return dict(row)


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _validate_agent_status(status: str) -> None:
    if status not in VALID_AGENT_STATUSES:
        raise ValueError(f"Invalid agent status: {status}")
