# Summary Agent PR 评审说明

> 评审分支：`pr-3`（提交 `b433375 feat(agent_summary): implement MVP with layered architecture`）  
> 评审日期：2026-05-25  
> 用途：组内 Code Review / 与 PR 作者沟通

---

## 总评

| 项目 | 结论 |
|------|------|
| 架构与分层 | ✅ 方向正确，符合 `AGENT.md` / `PLAN.md` |
| 库内 Agent 流程（Mock） | ✅ 主流程可跑通 |
| CI（ruff + pytest） | ❌ 当前预计失败 |
| HTTP 对外接口 | ❌ 未接入真实 Agent |
| 真实 LLM 模型 | ❌ 未接入，仍为 Mock |

**建议：修完「必须改」项后再 merge；若本 PR 只做骨架，请在 PR 描述中明确范围。**

---

## 必须改（不修 CI 会红）

### 1. 重命名 `agent_summary/http/` 目录

**问题**：`backend/pyproject.toml` 配置了：

```toml
pythonpath = [".", "agent_summary"]
```

`agent_summary/http/` 会遮蔽 Python 标准库 `http`，导致 FastAPI / 全仓 pytest 无法 import：

```
ImportError: cannot import name 'cookies' from 'http'
(.../backend/agent_summary/http/__init__.py)
```

**位置**：

- `backend/agent_summary/http/__init__.py`
- `backend/agent_summary/http/router.py`

**改法**：重命名为 `api/` 或 `routes/` 等，并更新引用与文档中的路径说明。

---

### 2. 添加 `pytest-asyncio` 依赖

**问题**：以下测试使用 `async def` + `@pytest.mark.asyncio`，但 `pyproject.toml` 未声明依赖：

- `agent_summary/tests/test_agent/test_summary_agent.py`（5 个）
- `agent_summary/tests/test_core/test_state.py` 中 `TestRouter`（3 个）

本地/CI 报错示例：

```
async def functions are not natively supported.
You need to install a suitable plugin for your async framework, for example: pytest-asyncio
```

**改法**：在 `backend/pyproject.toml` 的 `dev` 依赖中加入 `pytest-asyncio`，并配置例如：

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

**验证**：

```bash
cd backend
uv sync
uv run pytest agent_summary/tests -v
```

---

### 3. 通过 `ruff check`

**问题**：CI workflow（`.github/workflows/ci.yml`）包含 `uv run ruff check`。当前约 141 个问题，常见类型：

| 规则 | 说明 |
|------|------|
| I001 | import 顺序/格式不规范 |
| F401 | 未使用的 import |
| F841 | 未使用的变量 |

大量 `sys.path.insert` 与未使用 import 集中在 `agent_summary/` 各模块。

**改法**：

```bash
cd backend
uv run ruff check .
uv run ruff check . --fix
uv run ruff check .
```

能删除的 `sys.path.insert` 建议删除（`pyproject.toml` 已配置 `pythonpath`）。

---

## 建议改（功能与文档一致性）

### 4. HTTP 未接入主应用

| 文件 | 状态 |
|------|------|
| `backend/agent_summary/router.py` | 被 `app/main.py` 挂载，**仍是 Mock 字符串** |
| `backend/agent_summary/http/router.py` | 调用 `SummaryAgent`，**未被 include** |

**改法（二选一）**：

1. 本 PR 将 `main.py` 路由改为使用 `SummaryAgent`；或  
2. PR 描述写明：「本 PR 仅交付库内 Agent，HTTP 集成后续 PR」。

---

### 5. 未接入真实大模型

当前默认使用内置 `MockLLM`：

```python
class MockLLM:
    async def chat(self, prompt: str) -> str:
        return f"Mock summary for: {prompt[:50]}..."
```

`summarize()` 返回中 `provider` / `model` 均为 `"mock"`。

设计上应接入 `backend/llm_providers/`（member 8），通过 `SummaryAgent(llm_provider=...)` 注入，**本 PR 尚未实现**。

---

### 6. 路由与摘要策略不一致

- `SummaryAgent._setup_routes()` 可返回 `search` / `hierarchical` / `direct`
- `run()` 中 **仅对 `search` 做了分支**，`hierarchical` 未改变执行路径
- 实际摘要策略由 `SummarizeStep` + `select_strategy()` 决定
- `single_pass` 策略在 `summarize.py` 中 **无独立实现**

建议统一「Router 步骤名」与「Summarize 策略名」的职责，避免文档、测试、实现三套说法。

---

### 7. 测试数据与断言不一致

- `tests/conftest.py` 中 `long_article` 约 1.5k 字符，难以触发 `>8000` 的 hierarchical
- `tests/fixtures/long_article.md` 与 conftest 内嵌长文不一致
- `test_long_article_uses_correct_strategy` 可能因 `route:direct` 子串误通过

建议统一 fixture，使长文/新闻等场景能真实覆盖对应分支。

---

### 8. 其它代码质量

- [ ] 删除重复的 `sys.path.insert`（已有 `pythonpath`）
- [ ] 清理未使用 import（如 `PROMPT_VERSION`、`ToolCallRecord`）
- [ ] 修正 commit author 占位符（「你的用户名」）
- [ ] 修正 PR/commit 中「28 tests passing」等不准确表述

---

## 做得好的地方

- `core` / `analysis` / `steps` / `agent` 分层清晰，便于团队协作
- 分析层（语言检测、文章类型、分块、策略）单元测试覆盖较好
- `SummaryAgent` 在 Mock 下可完成：analyze → route → summarize → evaluate
- 适合作为后续接入 `llm_providers` 和真实 HTTP 的基础

---

## Merge 检查清单

合并前建议全部满足：

- [ ] `cd backend && uv run ruff check .` 通过
- [ ] `cd backend && uv run pytest` 通过（含 `tests/` 与 `agent_summary/tests/`）
- [ ] PR 描述说明：HTTP 是否本 PR 范围、是否仍为 Mock 模型
- [ ] `http/` 目录已重命名，无标准库冲突

---

## 本地验证命令

```bash
# 进入 backend
cd backend
uv sync

# 代码检查
uv run ruff check .

# 仅 Summary Agent 模块测试
uv run pytest agent_summary/tests -v

# 全仓 backend 测试（验证 http 冲突、healthz 等）
uv run pytest -v

# 手工跑 Mock Agent（不依赖 pytest-asyncio）
PYTHONPATH=".:agent_summary" uv run python -c "
import asyncio
from agent.summary_agent import SummaryAgent

async def main():
    content = open('agent_summary/tests/fixtures/short_article.md').read()
    print(await SummaryAgent().summarize('test-1', content))

asyncio.run(main())
"
```

临时本地验证 asyncio 测试（不写入仓库时）：

```bash
uv add --dev pytest-asyncio
uv run pytest agent_summary/tests -v
```

---

## 给 PR 作者的短评模板（可直接粘贴）

> 感谢提交 Summary Agent MVP，分层结构清晰。  
> 合并前请处理：  
> 1. 重命名 `agent_summary/http/`，避免遮蔽标准库导致全仓 pytest 失败；  
> 2. 在 `pyproject.toml` 添加 `pytest-asyncio`；  
> 3. `ruff check` 通过。  
> 另外 `main.py` 仍走 mock router，新 `http/router` 未接入；模型为 MockLLM，请在 PR 描述中说明本 PR 范围。  
> 修完后请在 PR 下回复 `uv run ruff check .` 与 `uv run pytest` 通过截图或日志。

---

## 参考文件

| 路径 | 说明 |
|------|------|
| `.github/workflows/ci.yml` | CI 流程 |
| `backend/pyproject.toml` | pytest / pythonpath 配置 |
| `backend/agent_summary/agent/summary_agent.py` | Agent 与 MockLLM |
| `backend/agent_summary/router.py` | 当前对外 Mock 路由 |
| `backend/app/main.py` | FastAPI 路由挂载 |
| `backend/llm_providers/AGENT.md` | 计划中的模型接入层 |
