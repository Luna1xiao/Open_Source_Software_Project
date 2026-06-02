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


def query_tags(
    keyword: str | None = None,
    db_path: Path | str | None = None,
) -> list[Tag]:
    sql = """
        SELECT
            tags.id,
            tags.name,
            (
                SELECT GROUP_CONCAT(alias)
                FROM tag_aliases
                WHERE tag_aliases.tag_id = tags.id
            ) AS aliases,
            COUNT(DISTINCT article_tags.article_id) AS usage_count,
            COUNT(DISTINCT articles.id) FILTER (WHERE articles.is_read = 0) AS unread_count
        FROM tags
        LEFT JOIN article_tags ON article_tags.tag_id = tags.id
        LEFT JOIN articles ON articles.id = article_tags.article_id
    """
    params: tuple[str, ...] = ()

    if keyword:
        like_keyword = f"%{keyword}%"
        sql += """
            WHERE tags.name LIKE ?
                OR EXISTS (
                    SELECT 1
                    FROM tag_aliases
                    WHERE tag_aliases.tag_id = tags.id
                        AND tag_aliases.alias LIKE ?
                )
        """
        params = (like_keyword, like_keyword)

    sql += """
        GROUP BY tags.id
        ORDER BY tags.name COLLATE NOCASE ASC
    """

    with connection(db_path) as conn:
        rows = conn.execute(sql, params).fetchall()

    return [_row_to_tag(row) for row in rows]


def _row_to_tag(row) -> Tag:
    aliases = row["aliases"].split(",") if row["aliases"] else []
    return Tag(
        id=row["id"],
        name=row["name"],
        aliases=aliases,
        usage_count=row["usage_count"],
        unread_count=row["unread_count"],
    )
