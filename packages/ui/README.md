## 前端运行方式

```bash
cd ./Open_Source_Software_Project
pnpm install
pnpm --filter ui dev
```

## 访问地址

```bash
http://127.0.0.1:5173/
```

## Backend 地址解析

前端不会在组件里手写 backend URL。运行时按下面顺序解析：

1. `VITE_MERCURY_BASE_URL`
2. `window.__BACKEND_PORT__`（Tauri 启动时由桌面壳注入）
3. 默认回退 `http://127.0.0.1:8000`

对应实现位置：

- `src/services/api/base-url.ts`
- `src/services/api/client.ts`

## 当前启动方式

浏览器开发：

```bash
pnpm --filter ui dev
# 如需真实数据和摘要接口，同时启动 backend
cd backend
uv run uvicorn app.main:app --reload --port 8000
```

桌面开发：

```bash
pnpm --filter desktop tauri:dev
```

桌面模式下，`apps/desktop` 负责：

- 选择空闲端口
- 启动 Python backend
- 等待 `/healthz`
- 向前端注入 `window.__BACKEND_PORT__`

## 前端服务层分工

前端组件只消费 UI 自己的 domain model，不直接处理 OpenAPI 生成类型。

- `src/services/api/base-url.ts`
  - 解析 backend base URL
- `src/services/api/client.ts`
  - 创建共享的 IPC client
- `src/services/api/mappers.ts`
  - 把 backend `snake_case` schema 映射为 UI `camelCase` model
- `src/services/api/index.ts`
  - 暴露 `loadAppData`、`loadEntry`、`requestSummary` 等 API
- `src/hooks/useAppData.ts`
  - 负责 feeds/tags/entries 初始加载与刷新
- `src/hooks/useFeedActions.ts`
  - 负责添加 feed、导入 OPML、同步 feeds 的状态和错误处理
- `src/hooks/useEntryCleaner.ts`
  - 负责首次阅读时触发内容清洗并刷新 entry
- `src/hooks/useSummaryAction.ts`
  - 负责摘要请求、错误态、以及请求成功后的 entry 刷新

## 当前已接入接口

- `GET /feeds`
- `POST /feeds`
- `POST /feeds/opml/import`
- `POST /feeds/sync-all`
- `GET /tags`
- `GET /entries`
- `GET /entries/{entry_id}`
- `GET /content/entries/{entry_id}/clean`
- `POST /agents/summary/generate`

详细契约见 [docs/ipc-contract.md](/d:/githubcode/Open_Source_Software_Project/docs/ipc-contract.md)。

## 手工验收

推荐先用桌面壳：

```bash
pnpm --filter desktop dev
```

或者先安装桌面包后直接打开应用。当前仓库自带一个可导入的 OPML 示例文件：

- [mercury-demo.opml](/d:/githubcode/Open_Source_Software_Project/docs/examples/mercury-demo.opml)

也可以直接添加单个 feed URL：

- `https://devblogs.microsoft.com/python/feed/`

页面操作顺序：

1. 点击 `Add Feed...` 并粘贴 feed URL，或点击 `Import OPML...` 选择示例文件。
2. 导入 OPML 时勾选 `Sync Now`，这样导入后会自动抓文章。
3. 在左侧选择一个 feed，点击任意文章。
4. 阅读区首次打开文章时会自动调用 `/content/entries/{id}/clean`，把原始 HTML 清洗成 reader HTML。
5. 点击摘要面板里的 `Summary`。

## 摘要模型配置

摘要功能现在支持两种模式：

1. 快速 smoke test
   - 如果没有配置 `LLM_API_KEY`，backend 默认会回退到 mock summary。
   - 这样可以先验证“点击摘要按钮后 UI 能刷新结果”。
2. 真实模型
   - 在启动桌面应用前设置环境变量，或复制 `backend/agent_summary/.env.example` 为 `backend/agent_summary/.env`。
   - 最少需要：

```env
LLM_API_KEY=your-real-api-key
LLM_BASE_URL=https://chat.ecnu.edu.cn/open/api/v1
LLM_MODEL=ecnu-max
LLM_USE_MOCK=false
```

如果是安装后的桌面应用，最稳妥的方式是先把这些环境变量加到系统/用户环境变量，再重新打开应用。

## 新增接口时怎么接

1. 先在 backend 的 schema 和 route 中完成接口。
2. 运行 `pnpm gen:types` 更新 `packages/shared-types/src/generated.ts`。
3. 在 `@mercury/ipc-client` 新增 typed wrapper，不要把业务状态写进去。
4. 在 `src/services/api/` 中补 mapper 和调用函数。
5. 如果组件需要异步状态，优先新增 hook，而不是在 `App.tsx` 里直接 `fetch`。
6. 保持 OpenAPI 类型停留在 API 层，组件继续只吃 `src/domain/types.ts`。

## 共享类型约束

- `packages/shared-types/src/generated.ts` 是契约产物，不应该手写业务类型副本。
- backend schema 或 route 变化后，必须同步更新 shared types。
- `@mercury/shared-types` 只在 API 层使用，不直接进入 UI 组件。
