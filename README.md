# copilot2api

将 GitHub Copilot 转换为 OpenAI 兼容接口，支持多账号调度、额度查询、调用统计和 React + HeroUI 管理控制台。请求协议依据项目中的 HAR 整理，使用 `/copilot_internal/user`、`/models`、`/chat/completions` 和 `/embeddings`。

## 功能

- OpenAI 兼容：`GET /v1/models`、`POST /v1/chat/completions`、`POST /v1/embeddings`
- 完整透传聊天参数和 SSE 事件，支持流式/非流式响应、工具调用及 `usage`
- 本地 SQLite 账号池，支持轮询/最少使用调度、失败冷却、限流与鉴权故障切换
- 账号添加、编辑、启停、删除、令牌更换及额度刷新
- Chat、Completions、Premium Interactions 额度与重置时间展示
- 请求数、Token 用量和最近请求统计，不保存聊天正文
- 可选 OpenAI API Key 和管理令牌鉴权
- React 19、HeroUI、Vite、Tailwind CSS 管理界面，支持深浅主题

## 快速开始

需要 Python 3.12+ 和 Bun（也可使用 npm/pnpm 构建前端）。

```bash
uv sync
cd web && bun install && bun run build && cd ..
uv run copilot2api
```

打开 <http://127.0.0.1:8000>。先在“账号池”中添加自己的 GitHub OAuth 令牌；服务会验证 Copilot Chat 权限并读取账号资料与额度。令牌只写入服务端 `data/copilot2api.db`，不会通过 API 回显。请妥善保护该数据库，不要导入或提交他人令牌、HAR 中的凭据。

开发模式可分别运行：

```bash
uv run copilot2api
# 另一个终端
cd web && bun run dev
```

Vite 开发地址为 <http://127.0.0.1:5173>，`/api` 和 `/v1` 会代理到 8000 端口。

## 调用接口

未配置 `COPILOT2API_API_KEYS` 时，可以省略 `Authorization`；生产环境建议务必配置。

```bash
curl http://127.0.0.1:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer YOUR_API_KEY' \
  -d '{
    "model": "gpt-4o-mini",
    "messages": [{"role": "user", "content": "你好"}],
    "stream": true,
    "stream_options": {"include_usage": true}
  }'
```

Python OpenAI SDK 只需修改 `base_url`：

```python
from openai import OpenAI

client = OpenAI(base_url="http://127.0.0.1:8000/v1", api_key="YOUR_API_KEY")
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "你好"}],
)
print(response.choices[0].message.content)
```

Copilot 中仅支持 `/responses` 的模型不会显示在 `/v1/models`；本服务当前转换 Chat Completions 与 Embeddings，不转换 Responses API。

## 配置

全部配置通过环境变量设置，修改后重启服务。

| 环境变量 | 默认值 | 说明 |
| --- | --- | --- |
| `COPILOT2API_HOST` | `127.0.0.1` | 监听地址；暴露到公网前请配置鉴权 |
| `COPILOT2API_PORT` | `8000` | 监听端口 |
| `COPILOT2API_DATABASE` | `data/copilot2api.db` | SQLite 数据库路径 |
| `COPILOT2API_WEB_DIST` | `web/dist` | 前端构建产物目录 |
| `COPILOT2API_API_KEYS` | 空 | OpenAI 接口 Key，多个 Key 用英文逗号分隔 |
| `COPILOT2API_ADMIN_TOKEN` | 空 | 管理 API 与 WebUI 登录令牌 |
| `COPILOT2API_TIMEOUT` | `180` | 上游请求超时秒数 |
| `COPILOT2API_POOL_STRATEGY` | `round_robin` | `round_robin` 或 `least_used` |
| `COPILOT2API_DOCS` | `true` | 是否开放 `/docs` |

示例：

```bash
export COPILOT2API_API_KEYS='sk-local-change-me'
export COPILOT2API_ADMIN_TOKEN='a-long-random-admin-token'
export COPILOT2API_POOL_STRATEGY='least_used'
uv run copilot2api
```

## 管理 API

管理接口使用 `X-Admin-Key: <COPILOT2API_ADMIN_TOKEN>`；未设置管理令牌时无需鉴权，仅建议在本机这样运行。

- `GET /api/overview`：账号、请求、Token 和额度汇总
- `GET|POST /api/accounts`：账号列表、验证并添加账号
- `PATCH|DELETE /api/accounts/{id}`：修改名称/令牌/启停、删除账号
- `POST /api/accounts/{id}/refresh`：刷新资料与额度
- `GET /api/accounts/{id}/quota?refresh=true`：查询单账号额度
- `GET /api/models`：获取完整模型目录与能力信息
- `GET /api/config`：查看非敏感运行配置
- `GET /api/health`：健康检查

账号池只调度已启用且未处于冷却期的账号。上游返回 429 时账号冷却 60 秒，401/403 冷却 5 分钟，服务端错误冷却 20 秒。流式响应一旦开始便不能透明切换账号，因为部分事件可能已经发送给客户端。

## 安全说明

默认仅监听回环地址。不要将未设置管理令牌的服务直接暴露到公网。OAuth 令牌以本地 SQLite 可用形式保存，服务会尝试将数据库权限设为 `0600`；请使用环境变量或密钥管理工具注入 API Key，避免写入版本库。项目中的 HAR 仅用于协议分析，应用不会自动读取或导入其中的账号。
