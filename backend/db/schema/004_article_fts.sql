CREATE VIRTUAL TABLE IF NOT EXISTS article_fts USING fts5(
  title,
  summary,
  plain_text,
  content='article_search',
  content_rowid='rowid'
);

INSERT INTO article_fts(rowid, title, summary, plain_text)
SELECT rowid, title, summary, plain_text
FROM article_search
WHERE rowid NOT IN (SELECT rowid FROM article_fts);

CREATE TRIGGER IF NOT EXISTS trg_article_search_ai
AFTER INSERT ON article_search
BEGIN
  INSERT INTO article_fts(rowid, title, summary, plain_text)
  VALUES (new.rowid, new.title, new.summary, new.plain_text);
END;

CREATE TRIGGER IF NOT EXISTS trg_article_search_ad
AFTER DELETE ON article_search
BEGIN
  INSERT INTO article_fts(article_fts, rowid, title, summary, plain_text)
  VALUES ('delete', old.rowid, old.title, old.summary, old.plain_text);
END;

CREATE TRIGGER IF NOT EXISTS trg_article_search_au
AFTER UPDATE ON article_search
BEGIN
  INSERT INTO article_fts(article_fts, rowid, title, summary, plain_text)
  VALUES ('delete', old.rowid, old.title, old.summary, old.plain_text);
  INSERT INTO article_fts(rowid, title, summary, plain_text)
  VALUES (new.rowid, new.title, new.summary, new.plain_text);
END;
