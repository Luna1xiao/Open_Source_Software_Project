# agent_summary — PLAN.md

## 执行计划

### 阶段 0：准备工作（Day 1）

#### 0.1 确认依赖接口
- [ ] 与 member 3 确认 `db` 模块接口
- [ ] 与 member 8 确认 `llm_providers` 接口
- [ ] 与 member 7 确认翻译 Agent HTTP 接口

#### 0.2 创建目录结构
```bash
mkdir -p agent_summary/{http,agent,steps,tools,core,analysis}
mkdir -p agent_summary/tests/{test_http,test_agent,test_steps,test_tools,test_core,test_analysis,fixtures}
```

#### 0.3 创建测试 fixtures
- [x] `short_article.md`
- [x] `medium_article.md`
- [x] `long_article.md`

---

### 阶段 1：核心层 (`core/`)（Day 2）

**从最底层开始，被所有层依赖。**

#### 1.1 `core/config.py` — 配置常量
```python
CHUNK_MAX_CHARS = 4000
EVAL_MIN_LENGTH = 50
PROMPT_VERSION = "v1"
DEFAULT_MAX_RETRIES = 3
DEFAULT_TIMEOUT = 30.0
```

#### 1.2 `core/state.py` — 状态定义
```python
from pydantic import BaseModel

class ArticleProfile(BaseModel):
    language: str
    length: int
    has_headings: bool
    article_type: str
    section_count: int
    needs_context: bool

class AgentState(BaseModel):
    entry_id: str
    content: str
    summary: str | None = None
    profile: ArticleProfile | None = None
    search_results: list[str] = []
    rag_context: list[dict] = []
    step_history: list[str] = []
    metadata: dict[str, Any] = {}
```

#### 1.3 `core/router.py` — 条件路由器
```python
class Router:
    def __init__(self):
        self.routes: list[tuple[Callable, str]] = []
    
    def add_route(self, condition: Callable, step_name: str): ...
    async def route(self, state: AgentState) -> str: ...
```

#### 1.4 `core/hooks.py` — 钩子系统
```python
class HookRegistry:
    def __init__(self): ...
    def on(self, event: str, callback: Callable): ...
    async def emit(self, event: str, data: Any): ...
```

#### 1.5 `core/tracer.py` — 执行追踪
```python
@dataclass
class ToolCallRecord:
    tool_name: str
    arguments: dict
    result: Any
    duration: float
    error: str | None = None

@dataclass
class RunResult:
    output: str
    steps: list[str]
    tool_calls: list[ToolCallRecord]
    total_duration: float
    token_usage: dict[str, int]
```

**测试** (`tests/test_core/`):
- [ ] `test_state.py` — ArticleProfile, AgentState 创建和序列化
- [ ] `test_router.py` — 条件匹配、默认路由
- [ ] `test_hooks.py` — 注册、触发、顺序
- [ ] `test_tracer.py` — 记录创建

---

### 阶段 2：分析层 (`analysis/`)（Day 3）

**内容处理逻辑，只依赖 core/。**

#### 2.1 `analysis/analyzer.py` — 文章分析
```python
from core.state import ArticleProfile

def analyze(markdown: str) -> ArticleProfile:
    language = detect_language(markdown)
    length = len(markdown)
    headings = re.findall(r'^#{1,3} ', markdown, re.MULTILINE)
    article_type = classify_article_type(markdown)
    needs_context = length > 5000 or article_type == "news"
    ...
```

#### 2.2 `analysis/chunker.py` — 文本分块
```python
def chunk_by_headings(markdown: str, max_chars: int = 4000) -> list[str]: ...
def chunk_by_paragraphs(text: str, max_chars: int = 4000) -> list[str]: ...
```

#### 2.3 `analysis/strategies.py` — 策略选择
```python
def select_strategy(profile: ArticleProfile) -> str:
    if profile.length < 2000:
        return "direct"
    elif profile.length < 8000:
        return "single_pass"
    else:
        return "hierarchical"
```

#### 2.4 `analysis/prompts.py` — Prompt 模板
```python
PROMPT_VERSION = "v1"
SUMMARY_PROMPTS = {
    "direct": "...",
    "hierarchical": "...",
    "merge": "...",
}
```

**测试** (`tests/test_analysis/`):
- [ ] `test_analyzer.py` — 语言检测、类型分类、长度测量
- [ ] `test_chunker.py` — 按标题分块、按段落分块
- [ ] `test_strategies.py` — 策略选择逻辑

---

### 阶段 3：工具层 (`tools/`)（Day 4）

**工具定义和管理，只依赖 core/。**

#### 3.1 `tools/base.py` — 工具基础设施
```python
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
    def __init__(self): ...
    def register(self, tool: Tool): ...
    def get(self, name: str) -> Tool | None: ...
    def list_tools(self) -> list[dict]: ...

async def invoke_tool_with_retry(tool: Tool, **kwargs) -> Any:
    """带重试和超时的工具调用"""
    ...
```

#### 3.2 `tools/web_search.py` — 网络搜索
```python
@tool(name="search_web", description="搜索网络获取背景信息")
async def search_web(query: str) -> list[str]:
    ...
```

#### 3.3 `tools/document_search.py` — RAG 搜索
```python
@tool(name="search_documents", description="搜索已有文档库（RAG）")
async def search_documents(query: str, feed_id: str, top_k: int = 5) -> list[dict]:
    ...
```

#### 3.4 `tools/translation.py` — 翻译 Agent 调用
```python
@tool(name="call_translation", description="调用翻译 Agent")
async def call_translation(entry_id: str, target_lang: str) -> str:
    ...
```

**测试** (`tests/test_tools/`):
- [ ] `test_base.py` — 装饰器、注册表、重试逻辑
- [ ] `test_web_search.py` — mock HTTP 调用
- [ ] `test_document_search.py` — mock HTTP 调用

---

### 阶段 4：步骤层 (`steps/`)（Day 5-6）

**独立的处理步骤，依赖 core/、tools/、analysis/。**

#### 4.1 `steps/base.py` — 步骤基类
```python
from abc import ABC, abstractmethod
from core.state import AgentState

class BaseStep(ABC):
    @abstractmethod
    async def execute(self, state: AgentState, agent) -> AgentState:
        ...
```

#### 4.2 `steps/analyze.py` — 分析步骤
```python
from steps.base import BaseStep
from analysis.analyzer import analyze

class AnalyzeStep(BaseStep):
    async def execute(self, state: AgentState, agent) -> AgentState:
        state.profile = analyze(state.content)
        state.step_history.append("analyze")
        return state
```

#### 4.3 `steps/search.py` — 搜索步骤
```python
from steps.base import BaseStep
from tools.base import invoke_tool_with_retry

class SearchStep(BaseStep):
    async def execute(self, state: AgentState, agent) -> AgentState:
        if not state.profile or not state.profile.needs_context:
            return state
        
        keywords = extract_keywords(state.content)
        search_tool = agent.tools.get("search_web")
        if search_tool:
            results = await invoke_tool_with_retry(search_tool, query=" ".join(keywords))
            state.search_results = results
        
        return state
```

#### 4.4 `steps/summarize.py` — 摘要步骤
```python
from steps.base import BaseStep
from analysis.strategies import select_strategy
from analysis.chunker import chunk_by_headings
from analysis.prompts import SUMMARY_PROMPTS

class SummarizeStep(BaseStep):
    async def execute(self, state: AgentState, agent) -> AgentState:
        strategy = select_strategy(state.profile)
        
        if strategy == "hierarchical":
            chunks = chunk_by_headings(state.content)
            summaries = [await agent.llm.chat(...) for chunk in chunks]
            state.summary = await agent.llm.chat(merge_prompt(summaries))
        else:
            state.summary = await agent.llm.chat(direct_prompt(state.content))
        
        return state
```

#### 4.5 `steps/evaluate.py` — 评估步骤
```python
from steps.base import BaseStep

class EvaluateStep(BaseStep):
    async def execute(self, state: AgentState, agent) -> AgentState:
        if state.summary and len(state.summary) < EVAL_MIN_LENGTH:
            state = await SummarizeStep().execute(state, agent)
        return state
```

#### 4.6 `steps/translate.py` — 翻译步骤
```python
from steps.base import BaseStep

class TranslateStep(BaseStep):
    async def execute(self, state: AgentState, agent) -> AgentState:
        translate_tool = agent.tools.get("call_translation")
        if translate_tool:
            state.translation = await invoke_tool_with_retry(
                translate_tool, entry_id=state.entry_id, target_lang="zh"
            )
        return state
```

**测试** (`tests/test_steps/`):
- [ ] `test_analyze.py` — 设置 profile
- [ ] `test_search.py` — 跳过/执行搜索
- [ ] `test_summarize.py` — direct/hierarchical 策略
- [ ] `test_evaluate.py` — 通过/重试

---

### 阶段 5：Agent 层 (`agent/`)（Day 7-8）

**编排步骤，依赖 steps/、tools/、core/。**

#### 5.1 `agent/summary_agent.py`
```python
from core.state import AgentState
from core.router import Router
from core.hooks import HookRegistry
from core.tracer import RunResult
from tools.base import ToolRegistry
from steps.analyze import AnalyzeStep
from steps.search import SearchStep
from steps.summarize import SummarizeStep
from steps.evaluate import EvaluateStep

class SummaryAgent:
    def __init__(self, llm_provider, tools: list[Tool] | None = None):
        self.llm = llm_provider
        self.tool_registry = ToolRegistry()
        self.hooks = HookRegistry()
        self.router = Router()
        
        for t in (tools or []):
            self.tool_registry.register(t)
        
        self._setup_routes()
    
    def _setup_routes(self):
        self.router.add_route(lambda s: s.profile and s.profile.needs_context, "search")
        self.router.add_route(lambda s: s.profile and s.profile.length > 8000, "hierarchical")
        self.router.add_route(lambda s: True, "direct")
    
    async def run(self, state: AgentState) -> tuple[AgentState, RunResult]:
        start_time = time()
        
        state = await AnalyzeStep().execute(state, self)
        next_step = await self.router.route(state)
        
        if next_step == "search":
            state = await SearchStep().execute(state, self)
        
        state = await SummarizeStep().execute(state, self)
        state = await EvaluateStep().execute(state, self)
        
        return state, RunResult(...)
    
    async def summarize(self, request: SummaryRequest) -> SummaryResult:
        # 检查缓存 → 获取文章 → 执行 Agent → 保存缓存
        ...
```

#### 5.2 `agent/digest_agent.py`
```python
class DigestAgent:
    async def digest(self, request: DigestRequest) -> DigestResult:
        # 获取多篇文章 → 各自摘要 → 合并
        ...
```

**测试** (`tests/test_agent/`):
- [ ] `test_summary_agent.py` — 缓存命中/未命中、执行流程
- [ ] `test_digest_agent.py` — 多篇合并

---

### 阶段 6：HTTP 层 (`http/`)（Day 9）

**最上层，只依赖 agent/。**

#### 6.1 `http/router.py`
```python
from fastapi import APIRouter
from app.schemas.agent import SummaryRequest, SummaryResult, DigestRequest, DigestResult

router = APIRouter(prefix="/agents/summary", tags=["agent-summary"])

@router.post("/", response_model=SummaryResult)
async def summarize(req: SummaryRequest):
    agent = get_summary_agent()
    return await agent.summarize(req)

@router.post("/digest", response_model=DigestResult)
async def digest(req: DigestRequest):
    agent = get_digest_agent()
    return await agent.digest(req)

@router.get("/{entry_id}", response_model=SummaryResult)
async def get_cached(entry_id: str):
    ...
```

**测试** (`tests/test_http/`):
- [ ] `test_router.py` — 200/404/500 响应

---

### 阶段 7：集成与验收（Day 10-12）

#### 7.1 集成测试
- [ ] 端到端流程测试
- [ ] 与 db/llm_providers 集成

#### 7.2 边界情况
- [ ] 空文章、超长文章、LLM 超时、工具失败

#### 7.3 验收
- [ ] `uv run pytest` 通过
- [ ] `uv run ruff check` 通过
- [ ] 测试覆盖率 > 90%

---

## 依赖关系图

```
http/router.py
    │
    ▼
agent/summary_agent.py
    │
    ├──→ steps/summarize.py ──→ analysis/prompts.py
    │                      ──→ analysis/chunker.py
    │                      ──→ analysis/strategies.py
    │
    ├──→ steps/search.py ──→ tools/web_search.py
    │
    ├──→ steps/analyze.py ──→ analysis/analyzer.py
    │
    └──→ steps/evaluate.py
    
    所有层 ──→ core/state.py
           ──→ core/router.py
           ──→ core/hooks.py
           ──→ core/tracer.py
           ──→ core/config.py
```

---

## 里程碑

| 里程碑 | 交付物 | 日期 |
|--------|--------|------|
| M0 | 目录结构、依赖确认 | Day 1 |
| M1 | 核心层 (core/) | Day 2 |
| M2 | 分析层 (analysis/) | Day 3 |
| M3 | 工具层 (tools/) | Day 4 |
| M4 | 步骤层 (steps/) | Day 6 |
| M5 | Agent 层 (agent/) | Day 8 |
| M6 | HTTP 层 (http/) | Day 9 |
| M7 | 集成测试通过 | Day 11 |
| M8 | 验收通过 | Day 12 |
