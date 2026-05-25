from pathlib import Path

from app.schemas.tag import Tag
from db.connection import connection


def save_tag(tag: Tag, db_path: Path | str | None = None) -> Tag:
    with connection(db_path) as conn:
        with conn:
            conn.execute(
                """
                INSERT INTO tags (id, name, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (tag.id, tag.name),
            )
            conn.execute("DELETE FROM tag_aliases WHERE tag_id = ?", (tag.id,))
            conn.executemany(
                "INSERT INTO tag_aliases (tag_id, alias) VALUES (?, ?)",
                [(tag.id, alias) for alias in tag.aliases],
            )
    return tag


def set_article_tags(
    article_id: str,
    tag_ids: list[str],
    db_path: Path | str | None = None,
) -> None:
    with connection(db_path) as conn:
        with conn:
            conn.execute("DELETE FROM article_tags WHERE article_id = ?", (article_id,))
            conn.executemany(
                "INSERT INTO article_tags (article_id, tag_id) VALUES (?, ?)",
                [(article_id, tag_id) for tag_id in tag_ids],
            )
