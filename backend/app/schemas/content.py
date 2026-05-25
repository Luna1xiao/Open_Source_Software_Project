from pydantic import BaseModel


class ArticleContent(BaseModel):
    article_id: str
    raw_html: str
    cleaned_html: str
    cleaned_markdown: str
    plain_text: str
    content_hash: str | None = None
