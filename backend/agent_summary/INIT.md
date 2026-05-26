# agent_summary — INIT.md

## 项目定义

### 目标
构建一个智能摘要 Agent，能够：
1. 自动生成单条文章摘要
2. 生成多篇文章的合并摘要（Digest）
3. 根据文章特征自适应选择摘要策略
4. 缓存结果避免重复调用 LLM
5. 支持工具调用（搜索、RAG）
6. 与其他 Agent 协作（翻译）

### 核心关注点
| 优先级 | 关注点 | 说明 |
|--------|--------|------|
| P0 | 摘要质量 | 输出必须准确、连贯、覆盖要点 |
| P0 | 缓存命中 | 相同输入不重复调用 LLM |
| P1 | 自适应策略 | 根据文章长度/类型选择不同处理方式 |
| P1 | 工具调用 | 支持搜索、RAG 等外部工具 |
| P2 | Agent 协作 | 与翻译 Agent 等协作 |
| P2 | 成本控制 | 分块策略避免 token 浪费 |

### 约束条件
- **依赖约束**：只能导入 `db` 和 `llm_providers`，不能导入其他 agent/模块
- **接口约束**：使用 `app/schemas/` 中的 Pydantic 模型
- **缓存键**：`(entry_id, provider, model, prompt_version)`
- **错误处理**：失败返回 `status="failure"`，不抛 500
- **无外部框架**：不引入 LangChain，自己实现 Agent 模式

---

## 技术选型：轻量 Agent 框架

### 设计理念

借鉴 LangChain 的核心模式，但自己实现：

| LangChain 概念 | 我们的实现 | 理由 |
|---------------|-----------|------|
| `Tool` | `@tool` 装饰器 + 注册表 | 保持简单，无外部依赖 |
| `Agent` | `BaseAgent` 基类 | 统一接口 |
| `Chain` | `Pipeline` 类 | 顺序执行步骤 |
| `State` | `AgentState` dataclass | 状态管理 |
| `Memory` | 数据库缓存 | 已有架构 |
| `Callback` | `logging` 模块 | 足够用 |

### 核心组件

```python
# 1. 工具系统
@tool(description="搜索网络获取背景信息")
async def search_web(query: str) -> list[str]:
    ...

# 2. Agent 基类
class BaseAgent:
    def __init__(self, llm_provider, tools: list[Tool]):
        self.llm = llm_provider
        self.tools = {t.name: t for t in tools}
    
    async def run(self, state: AgentState) -> AgentState:
        raise NotImplementedError

# 3. 管道执行
pipeline = Pipeline([
    AnalyzeStep(),
    SearchStep(),  # 可选
    SummarizeStep(),
    TranslateStep(),  # 可选
])
result = await pipeline.execute(initial_state)
```

---

## 数据探索

### 输入数据

**Entry 对象**（来自 `db.get_entry()`）：
```python
class Entry(BaseModel):
    id: str
    feed_id: str
    title: str
    summary: str          # RSS 原始摘要（可能为空）
    author: str
    url: str
    published_at: str
    is_read: bool
    is_starred: bool
    tag_ids: list[str]
    reader_html: str      # ← 主要输入：清理后的 HTML/Markdown
    web_preview: str
    related_entry_ids: list[str]
    note: str
    summary_text: str     # ← 存储生成的摘要
    translation_html: str | None
    translation_status: LongTaskStatus
```

### 输出数据

**SummaryResult**：
```python
class SummaryResult(BaseModel):
    entry_id: str
    summary_text: str     # ← 生成的摘要
    status: LongTaskStatus
    provider: str
    model: str
```

### 工具输入输出

**搜索工具**：
```python
# 输入
query: str  # 搜索关键词
# 输出
list[str]   # 搜索结果列表
```

**RAG 工具**：
```python
# 输入
query: str      # 查询内容
feed_id: str    # 订阅源 ID（限定范围）
top_k: int = 5  # 返回数量
# 输出
list[dict]      # 相关文档列表 [{"content": str, "score": float}]
```

**翻译 Agent（通过 HTTP）**：
```python
# 输入
entry_id: str
target_lang: str
# 输出
translation_html: str
```

---

## 成功标准

1. **功能完整**：支持单条摘要、批量摘要、工具调用
2. **缓存有效**：相同输入 100% 命中缓存
3. **策略自适应**：根据文章特征自动选择处理方式
4. **工具集成**：能调用搜索和 RAG 工具
5. **错误优雅**：失败返回明确错误信息
6. **测试覆盖**：核心逻辑 100% 测试覆盖
7. **代码质量**：`uv run ruff check` 通过

---

## 待讨论问题

- [x] 是否引入 LangChain → 不引入，自己实现
- [ ] RAG 实现方式：全文搜索 vs 向量搜索？
- [ ] 搜索 API：用什么服务？
- [ ] 翻译 Agent 接口：HTTP 路径和参数？
