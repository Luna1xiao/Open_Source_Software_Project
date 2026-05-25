# Mercury Storage Engineer Guide

面向角色：项目组 A 数据与内容组 - 存储工程师。

目标：从 0 到 1 实现 Mercury 的本地 SQLite 存储层，并保证 Windows / Linux / macOS 平台中立、可迁移、可测试、可被 Feed / Cleaner / Agent / UI 模块稳定调用。

## 1. 你的模块边界

存储模块位于 `backend/db/`，它是底层库，不是 HTTP 模块。

你负责：

- SQLite schema 设计与维护。
- 数据库连接、初始化、PRAGMA 配置。
- 版本化 migration。
- Feed / Article / Article Content / Agent Result / Provider Settings / App Config 的 CRUD。
- 本地文章缓存与 Feed 元数据缓存。
- Summary / Translation / TagAgent 等 Agent 输出存储。
- 为 Coding Agent 使用过程形成 `.agent-traces/` 持久化文档。

你不负责：

- Feed 网络抓取和 OPML 解析，这属于 `backend/feed_engine/`。
- HTML 清洗和 Markdown 转换，这属于 `backend/content_cleaner/`。
- LLM 调用和 Prompt 编排，这属于 `backend/agent_summary/`、`backend/agent_translation/`、`backend/llm_providers/`。
- 直接给前端提供接口。前端只通过 FastAPI route 访问，route 再调用你的 repository。

依赖方向必须保持：

```text
FastAPI routers / agents / feed_engine / content_cleaner
  -> backend/db repositories
  -> sqlite3
```

`backend/db` 不要反向 import 上层模块。

## 2. 平台中立原则

Mercury 是 local-first 桌面应用，SQLite 文件必须在三大系统上稳定工作。

### 2.1 数据文件位置

统一使用 `backend/app/config.py` 的 `settings.resolved_db_path()`：

```py
from app.config import settings

db_path = settings.resolved_db_path()
```

默认路径是：

```text
Path.home() / ".mercury" / "mercury.db"
```

允许用户通过环境变量覆盖：

```text
MERCURY_DATA_DIR=/custom/data/dir
MERCURY_DB_PATH=/custom/data/dir/mercury.db
```

实现时注意：

- 使用 `pathlib.Path`，不要手写 `/` 或 `\`。
- 初始化前 `db_path.parent.mkdir(parents=True, exist_ok=True)`。
- 测试使用临时目录或 `:memory:`，不要写真实用户目录。
- SQLite 路径入参保留 `Path | str`，方便单元测试注入。

### 2.2 SQLite PRAGMA

每个连接打开后执行：

```sql
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA busy_timeout = 5000;
PRAGMA synchronous = NORMAL;
```

原因：

- `foreign_keys=ON`：SQLite 默认不一定启用外键，必须显式打开。
- `journal_mode=WAL`：读写并发更好，适合本地 RSS 同步和 UI 查询同时发生。
- `busy_timeout=5000`：写入竞争时等待 5 秒，减少偶发 database is locked。
- `synchronous=NORMAL`：WAL 下性能和可靠性折中。

对 `:memory:` 数据库，`journal_mode=WAL` 可能不会生效，这是正常情况，测试不要硬断言 WAL 返回值。

## 3. 推荐目录结构

```text
backend/db/
  __init__.py
  connection.py
  migrations.py
  schema/
    001_initial.sql
  repositories/
    __init__.py
    feed_repo.py
    article_repo.py
    agent_repo.py
    config_repo.py
```

职责：

- `connection.py`：连接创建、row factory、PRAGMA、事务 helper。
- `migrations.py`：读取并执行 `schema/*.sql`，维护 `schema_migrations`。
- `schema/001_initial.sql`：首版表结构。
- `repositories/*`：只做 CRUD 和查询，不写复杂业务逻辑。
- `__init__.py`：导出稳定公共 API，例如 `init_db`, `save_article`, `get_article`。

## 4. 首版表结构

你的核心表包括：

- `feeds`
- `articles`
- `article_content`
- `agent_runs`
- `agent_steps`
- `provider_settings`
- `app_config`

建议首版 migration：

```sql
CREATE TABLE IF NOT EXISTS schema_migrations (
  version TEXT PRIMARY KEY,
  applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS feeds (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  site_url TEXT NOT NULL DEFAULT '',
  feed_url TEXT NOT NULL UNIQUE,
  description TEXT NOT NULL DEFAULT '',
  language TEXT,
  last_fetched_at TEXT,
  etag TEXT,
  last_modified TEXT,
  status TEXT NOT NULL DEFAULT 'idle',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_feeds_feed_url ON feeds(feed_url);

CREATE TABLE IF NOT EXISTS articles (
  id TEXT PRIMARY KEY,
  feed_id TEXT NOT NULL REFERENCES feeds(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  summary TEXT NOT NULL DEFAULT '',
  author TEXT NOT NULL DEFAULT '',
  url TEXT NOT NULL,
  guid TEXT,
  published_at TEXT,
  fetched_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  is_read INTEGER NOT NULL DEFAULT 0 CHECK (is_read IN (0, 1)),
  is_starred INTEGER NOT NULL DEFAULT 0 CHECK (is_starred IN (0, 1)),
  note TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(feed_id, guid),
  UNIQUE(feed_id, url)
);

CREATE INDEX IF NOT EXISTS idx_articles_feed_published ON articles(feed_id, published_at DESC);
CREATE INDEX IF NOT EXISTS idx_articles_read ON articles(is_read);
CREATE INDEX IF NOT EXISTS idx_articles_starred ON articles(is_starred);

CREATE TABLE IF NOT EXISTS article_content (
  article_id TEXT PRIMARY KEY REFERENCES articles(id) ON DELETE CASCADE,
  raw_html TEXT NOT NULL DEFAULT '',
  cleaned_html TEXT NOT NULL DEFAULT '',
  cleaned_markdown TEXT NOT NULL DEFAULT '',
  plain_text TEXT NOT NULL DEFAULT '',
  content_hash TEXT,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS agent_runs (
  id TEXT PRIMARY KEY,
  article_id TEXT REFERENCES articles(id) ON DELETE CASCADE,
  agent_type TEXT NOT NULL CHECK (agent_type IN ('summary', 'translation', 'tag')),
  status TEXT NOT NULL,
  provider TEXT NOT NULL DEFAULT '',
  model TEXT NOT NULL DEFAULT '',
  input_hash TEXT,
  target_lang TEXT,
  output_text TEXT,
  output_json TEXT,
  error_message TEXT,
  prompt_tokens INTEGER NOT NULL DEFAULT 0,
  completion_tokens INTEGER NOT NULL DEFAULT 0,
  total_tokens INTEGER NOT NULL DEFAULT 0,
  started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  finished_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_agent_runs_article_type ON agent_runs(article_id, agent_type);
CREATE INDEX IF NOT EXISTS idx_agent_runs_status ON agent_runs(status);

CREATE TABLE IF NOT EXISTS agent_steps (
  id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES agent_runs(id) ON DELETE CASCADE,
  step_index INTEGER NOT NULL,
  name TEXT NOT NULL,
  status TEXT NOT NULL,
  input_json TEXT,
  output_json TEXT,
  error_message TEXT,
  started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  finished_at TEXT,
  UNIQUE(run_id, step_index)
);

CREATE TABLE IF NOT EXISTS provider_settings (
  provider TEXT PRIMARY KEY,
  enabled INTEGER NOT NULL DEFAULT 0 CHECK (enabled IN (0, 1)),
  base_url TEXT,
  default_model TEXT,
  api_key_ref TEXT,
  settings_json TEXT NOT NULL DEFAULT '{}',
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS app_config (
  key TEXT PRIMARY KEY,
  value_json TEXT NOT NULL,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

设计说明：

- ID 统一用 `TEXT`，推荐 UUID / stable hash，避免跨模块传递整数自增 ID。
- 时间统一 ISO 8601 字符串，便于 JSON 和 TypeScript 展示。
- boolean 用 `INTEGER` 的 `0/1`，repository 转成 Python `bool`。
- `article_content` 和 `articles` 拆开，避免列表查询时加载大 HTML。
- `agent_runs.output_text` 存 summary / translation 的主要可展示结果。
- `agent_runs.output_json` 存结构化补充结果，例如标签列表、模型元信息、调试字段。
- `agent_steps` 是持久化 Agent Trace 的数据库形态，用来记录一次 Agent 执行内部步骤。
- `provider_settings.api_key_ref` 只存密钥引用，不直接存 API key 明文。

## 5. Migration 策略

实现要求：

1. 按文件名顺序执行 `backend/db/schema/*.sql`。
2. 每个 migration 在事务里执行。
3. 执行完成后写入 `schema_migrations(version)`。
4. 已执行过的 migration 跳过。
5. 新表或新字段只允许新增 migration，不直接修改旧 migration，除非项目还未合并主分支。

伪代码：

```py
def run_migrations(conn: sqlite3.Connection) -> None:
    conn.execute("CREATE TABLE IF NOT EXISTS schema_migrations (...)")
    applied = {row["version"] for row in conn.execute("SELECT version FROM schema_migrations")}
    for file in sorted(schema_dir.glob("*.sql")):
        if file.name in applied:
            continue
        with conn:
            conn.executescript(file.read_text(encoding="utf-8"))
            conn.execute("INSERT INTO schema_migrations(version) VALUES (?)", (file.name,))
```

验收标准：

- 空数据库可完整初始化。
- 重复执行 `init_db()` 不报错。
- 部分 migration 已执行时，只执行剩余 migration。
- migration 失败时不能写入 `schema_migrations`。

## 6. 公共接口设计

用户给出的 TypeScript 风格接口：

```ts
saveArticle()
getArticle()
saveAgentResult()
queryFeed()
```

在当前后端中应落成 Python repository API，并返回 `app.schemas` 里的 Pydantic model。

建议公共 API：

```py
def init_db(db_path: Path | str | None = None) -> None: ...

def save_feed(feed: Feed) -> Feed: ...
def get_feed(feed_id: str) -> Feed | None: ...
def query_feeds(keyword: str | None = None) -> list[Feed]: ...

def save_article(entry: Entry) -> Entry: ...
def get_article(article_id: str) -> Entry | None: ...
def list_articles(feed_id: str | None = None, limit: int = 50, offset: int = 0) -> list[Entry]: ...
def mark_article_read(article_id: str, is_read: bool) -> None: ...

def save_article_content(
    article_id: str,
    raw_html: str,
    cleaned_html: str,
    cleaned_markdown: str,
    plain_text: str,
) -> None: ...

def save_agent_result(result: SummaryResult | TranslationResult) -> str: ...
def get_latest_agent_result(article_id: str, agent_type: str, target_lang: str | None = None) -> dict | None: ...
def append_agent_step(run_id: str, name: str, status: str, input_json: dict, output_json: dict) -> None: ...
```

注意：

- repository 内部可以用 dict row，但对外不要泄漏 SQLite row。
- 上层如果需要分页、过滤、排序，你提供明确参数，不让上层拼 SQL。
- 对列表页优先返回轻量字段，进入详情页再取 `article_content`。
- `save_*` 使用 upsert，保证同步任务重复跑不会插入重复文章。

## 7. 与其他岗位的 mock 对接

### 7.1 Feed 工程师

Feed 工程师解析 RSS / Atom / OPML 后，把结果交给你：

```py
save_feed(feed)
save_article(entry)
save_article_content(article_id, raw_html, "", "", plain_text="")
```

你需要支持：

- 按 `feed_url` 去重。
- 按 `feed_id + guid` 或 `feed_id + url` 去重。
- 保存 `etag` 和 `last_modified`，方便下一次增量同步。

### 7.2 内容清洗工程师

Cleaner 读取原始内容，写回清洗结果：

```py
content = get_article_content(article_id)
save_article_content(
    article_id=article_id,
    raw_html=content.raw_html,
    cleaned_html=cleaned_html,
    cleaned_markdown=cleaned_markdown,
    plain_text=plain_text,
)
```

你需要支持：

- 原始 HTML 和 cleaned HTML 分离。
- cleaned markdown 可为空，但字段必须存在。
- 用 `content_hash` 判断内容是否变化，避免重复清洗。

### 7.3 Summary / Translation Agent

Agent 运行前创建 `agent_runs`，运行中追加 `agent_steps`，结束时写最终结果：

```py
run_id = start_agent_run(article_id, agent_type="summary", provider="openai", model="...")
append_agent_step(run_id, "load_article", "success", {}, {"article_id": article_id})
finish_agent_run(run_id, status="success", output_text=summary_text, usage=usage)
```

你需要支持：

- `status`: `idle | running | success | error` 或项目现有 `LongTaskStatus` 枚举值。
- token 用量存储。
- 失败时保存 `error_message`。
- 同一文章可以多次 summary / translation，查询时默认取最新成功结果。

## 8. Article Cache 设计

缓存目标不是做复杂缓存系统，而是让 local-first 阅读体验稳定：

- Feed list：存在 `feeds`。
- Article list：存在 `articles`，不加载大正文。
- Article detail：正文存在 `article_content`。
- Agent 输出：存在 `agent_runs`，可被 UI 重复打开，不必重复调用 LLM。

缓存失效建议：

- `raw_html` 变化时更新 `content_hash`。
- `content_hash` 变化后，上层可以将旧 summary / translation 标为过期，或新建 run。
- `last_fetched_at`、`etag`、`last_modified` 由 Feed 同步更新。

## 9. 测试清单

在 `backend/tests/` 增加存储测试。

必须覆盖：

- `init_db()` 在空库上创建全部表。
- 重复 `init_db()` 幂等。
- `save_feed()` + `get_feed()`。
- `save_article()` + `get_article()`。
- 同一文章重复保存会更新，不会重复插入。
- 删除 feed 后级联删除 articles / article_content / agent_runs。
- `save_agent_result()` 后能取回最新结果。
- migration 表记录版本。

建议测试写法：

```py
def test_save_and_get_article(tmp_path):
    db_path = tmp_path / "mercury-test.db"
    init_db(db_path)
    ...
```

如果使用 `:memory:`，要注意每个 sqlite 连接都是独立内存库。最简单的单元测试方式是使用 `tmp_path` 文件数据库，仍然很快，而且更接近真实 WAL 行为。

运行：

```bash
cd backend
uv run pytest
uv run ruff check
```

## 10. 实施顺序

第一天先做能跑通的骨架：

1. 新增 `connection.py`，实现 `connect(db_path=None)`。
2. 新增 `schema/001_initial.sql`。
3. 新增 `migrations.py`，实现 `init_db()`。
4. 在 `app/lifespan.py` 调用 `init_db()`。
5. 写 `test_migrations.py`。

第二天做 Feed / Article 存取：

1. 实现 `feed_repo.py`。
2. 实现 `article_repo.py`。
3. 支持 `save_feed/get_feed/query_feeds`。
4. 支持 `save_article/get_article/list_articles/save_article_content`。
5. 和 Feed 工程师用 mock 数据跑通同步链路。

第三天做 Agent 存储：

1. 实现 `agent_repo.py`。
2. 支持 `start_agent_run/append_agent_step/finish_agent_run`。
3. 支持 `save_agent_result/get_latest_agent_result`。
4. 和 Summary / Translation 工程师约定 `status/provider/model/token` 字段。

第四天补工程质量：

1. 完成级联删除、索引、分页、过滤。
2. 补测试覆盖重复保存、失败 agent run、migration 幂等。
3. 写 `.agent-traces/YYYY-MM-DD-<handle>-storage-layer.md`。
4. 更新 PR 描述，说明 schema 选择和跨平台处理。

## 11. Definition of Done

你的存储模块达到可合并状态时，应满足：

- Windows / Linux / macOS 都只依赖 Python 标准库 `sqlite3` 即可运行。
- 数据库路径通过 `settings.resolved_db_path()` 获取。
- `init_db()` 可重复调用，migration 有版本记录。
- 外键启用，WAL 启用，连接有超时设置。
- `feeds/articles/article_content/agent_runs/agent_steps/provider_settings/app_config` 已建表。
- repository API 不暴露 SQL 和 row tuple。
- 单元测试覆盖核心 CRUD 和 migration。
- `uv run pytest` 和 `uv run ruff check` 通过。
- 非平凡 Coding Agent 辅助过程写入 `.agent-traces/`。

## 12. Coding Agent 留痕模板

每次让 Coding Agent 帮你做设计、实现、重构、排错，都在 `.agent-traces/` 新增一个短文档。

文件名：

```text
.agent-traces/YYYY-MM-DD-<github-handle>-storage-layer.md
```

内容：

```markdown
# Storage Layer

- Member: <github handle>
- Date: 2026-05-25
- Agent: Codex
- Related PR: #<number or TBD>

## Goal
Implement Mercury's cross-platform SQLite storage layer for feeds, articles, content cache, and agent outputs.

## Approach
Use Python stdlib sqlite3, pathlib-based database paths, versioned SQL migrations, WAL mode, and repository functions that return Pydantic models.

## Decisions
Keep article body in article_content so article list queries stay lightweight. Store agent_runs and agent_steps separately so final results and process trace can both be queried.

## Surprises
TBD.

## Follow-ups
Add FTS search and richer tag tables after the first data chain is stable.
```

不要提交原始对话全文；提交摘要，越短越有价值。
