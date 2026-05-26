# agent_summary

Mercury RSS 阅读器的摘要 Agent 模块，负责自动生成文章摘要。

## 目录

- [架构](#架构)
- [快速开始](#快速开始)
- [API 接口](#api-接口)
- [使用示例](#使用示例)
  - [Storage API](#storage-api)
  - [Feed 示例](#feed-示例)
  - [Article 示例](#article-示例)
  - [Cleaner 示例](#cleaner-示例)
  - [Agent 示例](#agent-示例)
  - [测试示例](#测试示例)
- [模块结构](#模块结构)
- [配置](#配置)

---

## 架构

```
┌─────────────────────────────────────────────────────────┐
│  HTTP 层 (router.py)                                    │
│  接收前端请求，返回摘要结果                                │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  Agent 层 (agent/summary_agent.py)                      │
│  编排步骤，管理执行流程                                    │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  步骤层 (steps/)                                        │
│  analyze → search → summarize → evaluate                │
└─────────────────────────────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  分析层         │ │  工具层         │ │  LLM 客户端     │
│  (analysis/)    │ │  (tools/)       │ │  (llm_client.py)│
│  文章分析/分块  │ │  搜索/RAG       │ │  ECNU API       │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

---

## 快速开始

### 1. 安装依赖

```bash
cd backend
pip install pydantic fastapi
```

### 2. 配置 API

复制 `.env.example` 为 `.env` 并填入 API Key：

```bash
cd agent_summary
cp .env.example .env
# 编辑 .env 文件，填入真实的 API Key
```

`.env` 文件格式：
```env
LLM_API_KEY=your-api-key-here
LLM_BASE_URL=https://chat.ecnu.edu.cn/open/api/v1
LLM_MODEL=ecnu-max
```

### 3. 运行测试

```bash
# 运行所有测试（使用 Mock LLM，不调用真实 API）
python -m pytest agent_summary/tests/ -v

# 运行特定测试
python -m pytest agent_summary/tests/test_agent/ -v
```

### 4. 使用 Agent

```python
import asyncio
from agent_summary.agent.summary_agent import SummaryAgent

async def main():
    # 创建 Agent（使用真实 LLM，从 .env 读取配置）
    agent = SummaryAgent()
    
    # 生成摘要
    result = await agent.summarize(
        entry_id="article-001",
        content="人工智能正在改变世界..."
    )
    
    print(f"摘要: {result['summary_text']}")
    print(f"状态: {result['status']}")
    print(f"耗时: {result['duration']:.2f}s")

asyncio.run(main())
```

---

## API 接口

### POST /agents/summary/generate

生成文章摘要。

**请求:**
```json
{
  "entry_id": "article-001",
  "target_lang": "en"
}
```

**响应:**
```json
{
  "entry_id": "article-001",
  "summary": "这篇文章讨论了人工智能的发展..."
}
```

**curl 示例:**
```bash
curl -X POST http://127.0.0.1:8000/agents/summary/generate \
  -H "Content-Type: application/json" \
  -d '{"entry_id": "article-001", "target_lang": "en"}'
```

---

## 使用示例

### Storage API

Storage API 用于持久化存储摘要结果。`db` 模块提供 SQLite 存储。

```python
# 获取文章
entry = await db.get_entry(entry_id="article-001")
print(entry.reader_html)  # 文章内容（Markdown）

# 保存摘要
await db.save_summary(
    entry_id="article-001",
    summary_text="这是摘要内容",
    provider="ecnu",
    model="ecnu-max",
    prompt_version="v1",
    usage={"prompt_tokens": 100, "completion_tokens": 50}
)

# 获取缓存的摘要
cached = await db.get_summary(
    entry_id="article-001",
    provider="ecnu",
    model="ecnu-max",
    prompt_version="v1"
)
if cached:
    print(f"缓存命中: {cached.summary_text}")
```

---

### Feed 示例

Feed 模块负责抓取和解析 RSS/Atom 订阅源。

```python
# 添加订阅源
await db.add_feed(
    url="https://hnrss.org/frontpage",
    title="Hacker News"
)

# 获取订阅源列表
feeds = await db.list_feeds()
for feed in feeds:
    print(f"{feed.title}: {feed.url}")

# 同步订阅源（由 feed_engine 模块处理）
# POST /feeds/sync
# { "feed_id": "feed-001" }
```

---

### Article 示例

Article 是从 Feed 中获取的文章条目。

```python
# 获取文章
entry = await db.get_entry(entry_id="article-001")

# 文章结构
print(f"标题: {entry.title}")
print(f"作者: {entry.author}")
print(f"URL: {entry.url}")
print(f"发布时间: {entry.published_at}")
print(f"内容: {entry.reader_html}")  # 清理后的 Markdown
print(f"摘要: {entry.summary_text}")  # Agent 生成的摘要
print(f"翻译: {entry.translation_html}")  # 翻译 Agent 生成

# 获取未读文章
unread = await db.list_entries(feed_id="feed-001", is_read=False)

# 标记为已读
await db.mark_read(entry_id="article-001")
```

---

### Cleaner 示例

Content Cleaner 模块负责清理 HTML 内容，提取正文。

```python
# 清理 HTML（由 content_cleaner 模块处理）
# POST /content/clean
# { "entry_id": "article-001" }

# 返回清理后的内容
# {
#   "entry_id": "article-001",
#   "cleaned_html": "<p>清理后的 HTML</p>",
#   "reader_html": "清理后的 Markdown"
# }

# 使用场景
entry = await db.get_entry(entry_id="article-001")
if not entry.reader_html:
    # 先清理内容
    cleaned = await clean_content(entry.web_preview)
    entry.reader_html = cleaned.reader_html

# 然后使用 Agent 生成摘要
agent = SummaryAgent()
result = await agent.summarize(entry.id, entry.reader_html)
```

---

### Agent 示例

#### 基本使用

```python
import asyncio
from agent_summary.agent.summary_agent import SummaryAgent

async def main():
    # 创建 Agent（使用真实 LLM）
    agent = SummaryAgent()
    
    # 生成摘要
    result = await agent.summarize(
        entry_id="article-001",
        content="# 人工智能\n\n人工智能正在改变世界..."
    )
    
    print(f"摘要: {result['summary_text']}")
    print(f"状态: {result['status']}")
    print(f"耗时: {result['duration']:.2f}s")

asyncio.run(main())
```

#### 使用 Mock LLM（测试用）

```python
# 创建 Agent（使用 Mock LLM，不调用真实 API）
agent = SummaryAgent(use_mock=True)

result = await agent.summarize("test-001", "测试内容")
print(result['summary_text'])  # 输出: Mock summary for: ...
```

#### 自定义 LLM Provider

```python
from agent_summary.llm_client import LLMClient

# 使用自定义 API
custom_llm = LLMClient(
    api_key="your-api-key",
    base_url="https://api.example.com/v1",
    model="gpt-4"
)

agent = SummaryAgent(llm_provider=custom_llm)
result = await agent.summarize("article-001", "文章内容...")
```

#### 添加工具

```python
from agent_summary.tools.base import tool, Tool

# 定义工具
@tool(name="search_web", description="搜索网络获取背景信息")
async def search_web(query: str) -> list[str]:
    # 实现搜索逻辑
    return [f"搜索结果: {query}"]

# 创建 Agent 并注册工具
agent = SummaryAgent(tools=[search_web._tool_meta])
result = await agent.summarize("article-001", "文章内容...")
```

---

### 测试示例

#### 运行所有测试

```bash
cd backend
python -m pytest agent_summary/tests/ -v
```

#### 运行特定测试

```bash
# 测试 Agent 层
python -m pytest agent_summary/tests/test_agent/ -v

# 测试分析层
python -m pytest agent_summary/tests/test_analysis/ -v

# 测试核心层
python -m pytest agent_summary/tests/test_core/ -v
```

#### 编写测试

```python
import pytest
from agent_summary.agent.summary_agent import SummaryAgent
from agent_summary.core.state import AgentState

class TestSummaryAgent:
    @pytest.mark.asyncio
    async def test_summarize(self, short_article):
        # 使用 Mock LLM
        agent = SummaryAgent(use_mock=True)
        
        result = await agent.summarize("test-001", short_article)
        
        assert result["entry_id"] == "test-001"
        assert result["status"] == "success"
        assert len(result["summary_text"]) > 0
    
    @pytest.mark.asyncio
    async def test_run(self, short_article):
        agent = SummaryAgent(use_mock=True)
        state = AgentState(entry_id="test-001", content=short_article)
        
        state, result = await agent.run(state)
        
        assert "analyze" in state.step_history
        assert state.summary is not None
```

---

## 模块结构

```
agent_summary/
├── __init__.py
├── .env                   # API 配置（不提交到 Git）
├── .env.example           # API 配置示例
├── router.py              # HTTP 路由层
├── llm_client.py          # LLM 客户端（从 .env 读取配置）
├── AGENT.md               # Agent 指南
├── INIT.md                # 项目初始化文档
├── PLAN.md                # 执行计划
├── README.md              # 本文件
│
├── core/                  # 核心层
│   ├── state.py           # 状态定义
│   ├── router.py          # 条件路由器
│   ├── hooks.py           # 钩子系统
│   ├── tracer.py          # 执行追踪
│   └── config.py          # 配置常量
│
├── analysis/              # 分析层
│   ├── analyzer.py        # 文章分析器
│   ├── chunker.py         # 文本分块器
│   ├── strategies.py      # 策略选择
│   └── prompts.py         # Prompt 模板
│
├── tools/                 # 工具层
│   └── base.py            # 工具基础设施
│
├── steps/                 # 步骤层
│   ├── base.py            # 步骤基类
│   ├── analyze.py         # 分析步骤
│   ├── search.py          # 搜索步骤
│   ├── summarize.py       # 摘要步骤
│   ├── evaluate.py        # 评估步骤
│   └── translate.py       # 翻译步骤
│
├── agent/                 # Agent 层
│   └── summary_agent.py   # SummaryAgent
│
└── tests/                 # 测试
    ├── conftest.py
    ├── fixtures/
    ├── test_core/
    ├── test_analysis/
    └── test_agent/
```

---

## 配置

### LLM 配置

API 配置通过 `.env` 文件管理（**不要提交到 Git**）：

```env
# agent_summary/.env
LLM_API_KEY=sk-xxx              # API Key
LLM_BASE_URL=https://...        # API 地址
LLM_MODEL=ecnu-max              # 模型名称
```

也可以通过环境变量设置：

```bash
export LLM_API_KEY=sk-xxx
export LLM_BASE_URL=https://chat.ecnu.edu.cn/open/api/v1
export LLM_MODEL=ecnu-max
```

或在代码中直接传入：

```python
from agent_summary.llm_client import LLMClient

client = LLMClient(
    api_key="sk-xxx",
    base_url="https://api.example.com/v1",
    model="gpt-4"
)
```

### 策略配置

```python
# agent_summary/core/config.py
DIRECT_THRESHOLD = 2000         # 短文阈值
SINGLE_PASS_THRESHOLD = 8000    # 中等长度阈值
CHUNK_MAX_CHARS = 4000          # 分块最大字符数
```

### 缓存键

```python
(entry_id, provider, model, prompt_version)
```

---

## 依赖关系

```
agent_summary 可以导入:
├── db                    ✅ (member 3 负责)
├── llm_providers         ✅ (member 8 负责)
└── app/schemas/*         ✅ (tech lead 维护)

agent_summary 禁止导入:
├── feed_engine           ❌ (member 1 负责)
├── content_cleaner       ❌ (member 5 负责)
└── agent_translation     ❌ (member 7 负责，通过 HTTP 调用)
```
