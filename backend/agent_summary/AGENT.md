# agent_summary — Agent Guide

**Owner**: member 6 (Summary Agent Engineer)

## Mission

构建一个智能摘要 Agent，能够根据文章特征自适应选择摘要策略，支持工具调用（搜索、RAG）和与其他 Agent 协作（翻译）。

## 模块分层架构

```
┌─────────────────────────────────────────────────────────────┐
│  HTTP 层 (http/)                                            │
│  - 接收请求，返回响应                                        │
│  - 参数校验，错误处理                                        │
│  - 不包含业务逻辑                                            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Agent 层 (agent/)                                          │
│  - 编排多个步骤                                              │
│  - 管理执行状态                                              │
│  - 协调工具调用                                              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  步骤层 (steps/)                                            │
│  - 每个步骤独立、可复用                                      │
│  - 通过依赖注入获取工具和 LLM                                │
│  - 不关心执行顺序（由 Agent 层决定）                         │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  工具层 (tools/) │ │  分析层         │ │  核心层 (core/)  │
│  - 工具定义      │ │  (analysis/)    │ │  - 状态管理      │
│  - 工具注册      │ │  - 内容分析     │ │  - 路由逻辑      │
│  - 重试/超时     │ │  - 分块策略     │ │  - 钩子系统      │
│                 │ │  - Prompt 模板  │ │  - 执行追踪      │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

### 依赖规则

```
http/ → agent/ → steps/ → tools/ + analysis/
                              ↓
                            core/ (被所有层依赖)
```

- **上层可以依赖下层，下层不能依赖上层**
- **同层模块尽量不互相依赖**
- **core/ 是最底层，被所有层依赖**

---

## 模块职责

### HTTP 层 (`http/`)

**职责**：处理 HTTP 请求/响应，不含业务逻辑。

```python
# http/router.py
from fastapi import APIRouter
from app.schemas.agent import SummaryRequest, SummaryResult

router = APIRouter(prefix="/agents/summary", tags=["agent-summary"])

@router.post("/", response_model=SummaryResult)
async def summarize(req: SummaryRequest):
    agent = get_summary_agent()
    return await agent.summarize(req)
```

### Agent 层 (`agent/`)

**职责**：编排步骤，管理执行流程。

```python
# agent/summary_agent.py
from core.state import AgentState
from core.router import Router
from steps.analyze import AnalyzeStep
from steps.search import SearchStep
from steps.summarize import SummarizeStep
from steps.evaluate import EvaluateStep

class SummaryAgent:
    def __init__(self, llm_provider, tools):
        self.llm = llm_provider
        self.tools = tools
        self.router = Router()
        self._setup_routes()
    
    def _setup_routes(self):
        self.router.add_route(lambda s: s.profile.needs_context, "search")
        self.router.add_route(lambda s: s.profile.length > 8000, "hierarchical")
        self.router.add_route(lambda s: True, "direct")
    
    async def run(self, state: AgentState) -> AgentState:
        state = await AnalyzeStep().execute(state, self)
        next_step = await self.router.route(state)
        
        if next_step == "search":
            state = await SearchStep().execute(state, self)
        
        state = await SummarizeStep().execute(state, self)
        state = await EvaluateStep().execute(state, self)
        
        return state
```

### 步骤层 (`steps/`)

**职责**：每个步骤独立完成一个任务。

```python
# steps/base.py
from abc import ABC, abstractmethod
from core.state import AgentState

class BaseStep(ABC):
    @abstractmethod
    async def execute(self, state: AgentState, agent) -> AgentState:
        ...

# steps/summarize.py
from steps.base import BaseStep
from analysis.strategies import select_strategy
from analysis.chunker import chunk_by_headings
from analysis.prompts import SUMMARY_PROMPTS

class SummarizeStep(BaseStep):
    async def execute(self, state: AgentState, agent) -> AgentState:
        strategy = select_strategy(state.profile)
        
        if strategy == "hierarchical":
            chunks = chunk_by_headings(state.content)
            summaries = []
            for chunk in chunks:
                s = await agent.llm.chat(SUMMARY_PROMPTS["hierarchical"].format(content=chunk))
                summaries.append(s)
            state.summary = await agent.llm.chat(
                SUMMARY_PROMPTS["merge"].format(chunk_summaries="\n".join(summaries))
            )
        else:
            state.summary = await agent.llm.chat(
                SUMMARY_PROMPTS["direct"].format(content=state.content)
            )
        
        return state
```

### 工具层 (`tools/`)

**职责**：定义和管理可调用的工具。

```python
# tools/base.py
from dataclasses import dataclass
from typing import Callable

@dataclass
class Tool:
    name: str
    description: str
    parameters: dict
    func: Callable
    max_retries: int = 3
    timeout: float = 30.0

def tool(func=None, *, name=None, description=None):
    """装饰器：自动从函数签名生成工具定义"""
    ...

class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, Tool] = {}
    
    def register(self, tool: Tool): ...
    def get(self, name: str) -> Tool | None: ...

# tools/web_search.py
from tools.base import tool

@tool(name="search_web", description="搜索网络获取背景信息")
async def search_web(query: str) -> list[str]:
    ...
```

### 分析层 (`analysis/`)

**职责**：内容分析、分块、策略选择。

```python
# analysis/analyzer.py
from core.state import ArticleProfile

def analyze(markdown: str) -> ArticleProfile:
    ...

# analysis/chunker.py
def chunk_by_headings(markdown: str, max_chars: int = 4000) -> list[str]:
    ...

# analysis/strategies.py
def select_strategy(profile: ArticleProfile) -> str:
    ...

# analysis/prompts.py
PROMPT_VERSION = "v1"
SUMMARY_PROMPTS = {...}
```

### 核心层 (`core/`)

**职责**：共享基础设施，被所有层依赖。

```python
# core/state.py
from pydantic import BaseModel

class ArticleProfile(BaseModel):
    ...

class AgentState(BaseModel):
    ...

# core/router.py
class Router:
    ...

# core/hooks.py
class HookRegistry:
    ...

# core/tracer.py
@dataclass
class RunResult:
    ...

# core/config.py
CHUNK_MAX_CHARS = 4000
EVAL_MIN_LENGTH = 50
DEFAULT_MAX_RETRIES = 3
DEFAULT_TIMEOUT = 30.0
```

---

## 完整目录结构

```
agent_summary/
├── __init__.py
├── AGENT.md
├── INIT.md
├── PLAN.md
│
├── http/
│   ├── __init__.py
│   └── router.py
│
├── agent/
│   ├── __init__.py
│   ├── summary_agent.py
│   └── digest_agent.py
│
├── steps/
│   ├── __init__.py
│   ├── base.py
│   ├── analyze.py
│   ├── search.py
│   ├── summarize.py
│   ├── evaluate.py
│   └── translate.py
│
├── tools/
│   ├── __init__.py
│   ├── base.py
│   ├── web_search.py
│   ├── document_search.py
│   └── translation.py
│
├── core/
│   ├── __init__.py
│   ├── state.py
│   ├── router.py
│   ├── hooks.py
│   ├── tracer.py
│   └── config.py
│
├── analysis/
│   ├── __init__.py
│   ├── analyzer.py
│   ├── chunker.py
│   ├── strategies.py
│   └── prompts.py
│
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── fixtures/
    │   ├── short_article.md
    │   ├── medium_article.md
    │   └── long_article.md
    ├── test_http/
    │   └── test_router.py
    ├── test_agent/
    │   ├── test_summary_agent.py
    │   └── test_digest_agent.py
    ├── test_steps/
    │   ├── test_analyze.py
    │   ├── test_search.py
    │   ├── test_summarize.py
    │   └── test_evaluate.py
    ├── test_tools/
    │   ├── test_base.py
    │   ├── test_web_search.py
    │   └── test_document_search.py
    ├── test_core/
    │   ├── test_state.py
    │   ├── test_router.py
    │   ├── test_hooks.py
    │   └── test_tracer.py
    └── test_analysis/
        ├── test_analyzer.py
        ├── test_chunker.py
        └── test_strategies.py
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

外部依赖:
├── httpx                 # HTTP 客户端
├── pydantic              # 已有依赖
└── 无 LangChain          # 自己实现
```

---

## 验收标准

1. 长文章按语义分块，合并时调用 LLM 生成连贯摘要
2. 相同 `(entry_id, provider, model, prompt_version)` 返回缓存结果
3. 失败返回 `status="failure"` 并附带错误信息
4. Token 用量记录到 `usage_repo`
5. Prompt 模板版本化，版本号纳入缓存键
6. 支持工具调用（搜索、RAG），带重试和超时
7. 支持与翻译 Agent 协作（通过 HTTP）
8. 条件路由根据文章特征选择处理策略
9. 执行追踪记录完整过程
10. `uv run pytest` 和 `uv run ruff check` 通过

---

## 参考项目

- [edge-agent](https://github.com/danieldagot/edge-agent) — 零依赖、工具链、Chain 编排
- [pureagents](https://github.com/jmbarrancoml/pureagents) — ~1500 行、工具、路由、规划
- [pop](https://github.com/WYSIATI/pop) — 5 核心概念、2 依赖
- [agentsilex](https://github.com/howl-anderson/agentsilex) — ~300 行、透明、可修改
- [pyDigestor](https://github.com/jschell/pyDigestor) — RSS + FTS5 + TF-IDF
- [condenseit](https://github.com/wildlifechorus/condenseit) — 偏好学习、聚类

---

## 参考文档

- `app/schemas/agent.py` — 请求/响应模型
- `llm_providers/AGENT.md` — LLM 提供商接口
- `db/AGENT.md` — 数据库接口
- `backend/AGENT.md` — 后端通用规范
