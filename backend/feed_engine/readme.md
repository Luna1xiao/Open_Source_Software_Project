# Mercury Feed Engine

本模块负责 Mercury 后端的 Feed 数据解析、订阅导入导出和同步。实现位置固定在
`backend/feed_engine/`，不再经过 `packages/feed-engine`。

## 模块边界

Feed Engine 负责：

- RSS 2.0 解析
- Atom 解析
- Feed Validation
- OPML Import
- OPML Export
- Incremental Sync 的后端入口
- 将解析结果转换为 `app.schemas.feed.Feed` 和 `app.schemas.entry.Entry`

Feed Engine 不负责：

- 直接写 SQLite SQL
- 内容清洗、Markdown 转换
- 摘要、翻译、LLM 调用
- UI 状态和交互

所有持久化必须通过 `backend/db/README.md` 中定义的 storage API：

```py
from db import (
    delete_feed,
    get_feed,
    query_feeds,
    save_feed,
    save_articles,
    update_feed_sync_metadata,
)
```

当前仓库里的 `backend/db/__init__.py` 仍为空，因此 Feed Engine 使用运行时导入：
后端可以正常启动；当调用需要存储的接口而 storage API 尚未实现时，会返回
`503 STORAGE_UNAVAILABLE`，并指出缺失的函数名。

## HTTP API

路由统一挂载在 `/feeds`。

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/feeds` | 查询所有订阅，支持 `?q=` 搜索 |
| `POST` | `/feeds` | 订阅 feed URL，可选择立即同步 |
| `DELETE` | `/feeds/{feed_id}` | 删除订阅 |
| `POST` | `/feeds/parse` | 抓取并解析一个 feed，但不保存 |
| `POST` | `/feeds/validate` | 校验上传的 RSS/Atom XML |
| `POST` | `/feeds/{feed_id}/sync` | 同步单个订阅 |
| `POST` | `/feeds/sync-all` | 同步所有订阅 |
| `POST` | `/feeds/opml/import` | 导入 OPML，支持 raw XML body 或 multipart file |
| `GET` | `/feeds/opml/export` | 导出 OPML 文件 |

## Service API

主要入口在 `service.py`：

```py
await parse_feed(url)
await subscribe_feed(url, sync=True)
list_feeds(query=None)
delete_feed(feed_id)
await sync_feed(feed_id)
await sync_all_feeds()
import_opml(payload)
export_opml()
```

解析函数返回内部模型 `ParsedFeed` / `ParsedEntry`。保存前会转换为项目统一的
Pydantic schema：

- `app.schemas.feed.Feed`
- `app.schemas.entry.Entry`

## RSS / Atom 映射

RSS 2.0：

- `channel.title` -> `Feed.title`
- `channel.link` -> `Feed.site_url`
- `item.guid` / `item.link` -> 稳定文章 ID 来源
- `item.title` -> `Entry.title`
- `item.description` -> `Entry.summary`
- `content:encoded` 优先写入 `Entry.reader_html`
- `item.pubDate` -> ISO UTC `Entry.published_at`
- `dc:creator` / `author` -> `Entry.author`

Atom：

- `feed.title` -> `Feed.title`
- `feed.link rel="alternate"` -> `Feed.site_url`
- `entry.id` / `entry.link` -> 稳定文章 ID 来源
- `entry.title` -> `Entry.title`
- `entry.summary` -> `Entry.summary`
- `entry.content` 优先写入 `Entry.reader_html`
- `entry.published` / `entry.updated` -> ISO UTC `Entry.published_at`
- `entry.author.name` -> `Entry.author`

## ID 与幂等同步

Feed ID：

```text
feed-<sha256(normalized_feed_url)[:16]>
```

Article ID：

```text
article-<sha256(feed_id + stable_entry_source)[:24]>
```

`stable_entry_source` 优先级：

1. RSS `guid` / Atom `id`
2. 文章 URL
3. `title + published_at`

这样可以配合 `db.save_articles()` 的 upsert 语义，保证重复同步不会生成重复文章。

## OPML

导入：

- 递归读取嵌套 `<outline>`
- 只导入包含 `xmlUrl` 的节点
- `title` 优先，其次 `text`，最后使用 `xmlUrl`
- 同一个 OPML 文件中重复的 `xmlUrl` 会跳过并返回 warning
- 已存在的 feed 由 `get_feed(feed.id)` 判断后跳过

导出：

- 使用 OPML 2.0
- 从 `query_feeds()` 获取订阅
- 输出 `text`、`title`、`xmlUrl`、`htmlUrl`
- 自动转义 XML 特殊字符

## 错误格式

模块统一抛出 `FeedEngineError`，路由层转换为 FastAPI `HTTPException`。

```json
{
  "detail": "Feed request failed.",
  "code": "FETCH_FAILED",
  "context": {}
}
```

常见错误码：

- `INVALID_URL`
- `FETCH_FAILED`
- `FETCH_TIMEOUT`
- `INVALID_XML`
- `UNSUPPORTED_FEED`
- `OPML_INVALID`
- `FEED_NOT_FOUND`
- `STORAGE_UNAVAILABLE`

## 测试

当前测试在 `backend/tests/test_feed_engine.py`，fixture 在 `backend/tests/fixtures/`。

推荐验证：

```bash
cd backend
uv run ruff check
uv run pytest
```

如果本机没有 `uv`，可使用已安装依赖的 Python 环境近似验证：

```bash
python -m ruff check
python -m pytest
```

## 后续对接点

- Storage Engineer 实现 `backend/db/__init__.py` 导出的 repository API 后，存储型接口会自动开始工作。
- 如果 DB 后续能从 `get_feed()` 返回 `etag` / `last_modified`，`sync_feed()` 已经会自动带上条件请求头。
- Content Cleaner 可从 `Entry.reader_html` 或后续 `article_content.raw_html` 读取原始内容进行清洗。
- UI / IPC Client 可以把本模块 HTTP API 包装成 `parseFeed(url)`、`importOPML(file)`、`exportOPML()`、`syncFeed(feedId)`。
