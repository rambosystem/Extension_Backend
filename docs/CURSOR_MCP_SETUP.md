# 在 Cursor 中使用 Lokalise MCP

让 Cursor 里的 AI 能用 Lokalise 能力（列项目、加 Key、下载翻译、Key/Tag 联想等），需配置 MCP。

---

## 一、推荐：command + args + env（与 mcp-atlassian 同一种模式）

和 mcp-atlassian 一样，用 **command** 启动本地进程，通过 **env** 传 Token 和后端地址。在 `mcp.json` 里加一段即可（与现有 mcp-atlassian 并列）：

```json
{
  "mcpServers": {
    "mcp-atlassian": {
      "command": "uvx",
      "args": ["mcp-atlassian"],
      "env": {
        "JIRA_URL": "https://pacvue-enterprise.atlassian.net",
        "JIRA_USERNAME": "rambo.wang@pacvue.com",
        "JIRA_API_TOKEN": "xxx",
        "CONFLUENCE_URL": "https://pacvue-enterprise.atlassian.net/wiki",
        "CONFLUENCE_USERNAME": "rambo.wang@pacvue.com",
        "CONFLUENCE_API_TOKEN": "xxx"
      }
    },
    "mcp-lokalise": {
      "command": "node",
      "args": ["E:\\path\\to\\extension_backend\\mcp\\lokalise\\src\\index.js"],
      "env": {
        "LOKALISE_API_TOKEN": "你的Lokalise_API_Token",
        "EXTENSION_BACKEND_BASE_URL": "http://43.142.250.179:8000"
      }
    }
  }
}
```

**说明：**

- `args` 填你本机 **extension_backend** 仓库里 `mcp/lokalise/src/index.js` 的**绝对路径**（Windows 反斜杠写两遍 `\\`）。
- 若本机没有 extension_backend，可从服务器或 Git 只拷 **mcp/lokalise** 这一层目录到本机（如 `E:\tools\mcp-lokalise`），在该目录执行一次 `npm install`，然后 `args` 改为：`["E:\\tools\\mcp-lokalise\\src\\index.js"]`。
- 本机需已安装 **Node.js**（18+）。保存 `mcp.json` 后**完全重启 Cursor** 即可。

---

## 二、备选：服务器起 MCP HTTP 服务，本地用 URL 连（无需本机拷代码）

extension_backend 在**服务器**上时，可以把 MCP 也跑在服务器上，Cursor 在本机（如 E:\Workspace\Jira）**直接填 URL** 即可，不用在本机拷贝或运行任何 MCP 代码。

### 步骤 1：在服务器上以 HTTP 模式启动 MCP

在部署了 extension_backend 的机器上，进入 `mcp/lokalise` 目录，设置环境变量并启动：

```bash
cd /path/to/extension_backend/mcp/lokalise
export LOKALISE_API_TOKEN=你的Token
export EXTENSION_BACKEND_BASE_URL=http://43.142.250.179:8000   # 或你的后端地址
export MCP_HTTP_PORT=3100
npm install
node src/index.js
```

（可用 pm2、systemd 等常驻；Windows 服务器可设环境变量后 `node src/index.js`。）

MCP 会监听 `http://0.0.0.0:3100/sse`（路径可通过 `MCP_HTTP_PATH` 修改）。

### 步骤 2：本机 Cursor 里配置 MCP（只填 URL）

1. 打开/创建**全局** MCP 配置：
   - **Windows**: `%USERPROFILE%\.cursor\mcp.json`
   - **macOS/Linux**: `~/.cursor\mcp.json`
2. 写入（把地址换成你**服务器**的真实地址和端口）：

```json
{
  "mcpServers": {
    "mcp-lokalise": {
      "url": "http://43.142.250.179:3100/sse"
    }
  }
}
```

若 MCP 做了鉴权，可加 `headers`，例如：

```json
{
  "mcpServers": {
    "mcp-lokalise": {
      "url": "http://43.142.250.179:3100/sse",
      "headers": {
        "Authorization": "Bearer 你的鉴权Token"
      }
    }
  }
}
```

3. **完全重启 Cursor**，打开任意项目（如 E:\Workspace\Jira）即可使用。无需在本机安装 Node 或拷贝 MCP 代码。

若 MCP 通过 Nginx 等做了 HTTPS 反向代理，`url` 改为 `https://你的域名/sse` 即可。

---

## 三、在服务器上打开 extension_backend 仓库时（SSH / Remote）

若你是在服务器上直接打开 extension_backend 用 Cursor，可用仓库内自带的 `.cursor/mcp.json`（stdio 方式），填好 `LOKALISE_API_TOKEN`、在 `mcp/lokalise` 下执行 `npm install`、重启 Cursor 即可。

---

## 四、验证是否生效

- 重启后，在 Cursor 设置里看 **Features → MCP**（或 **Tools & MCP**）是否列出 `mcp-lokalise` 且无报错。
- 在 AI 对话里让模型执行：列出 Lokalise 项目、或给某个项目加一个翻译 Key，能正常调用即表示配置成功。

## 五、可用工具速览

| 工具 | 说明 |
|------|------|
| `list_projects` | 列出 Lokalise 项目 |
| `list_languages` | 列出某项目的语言 |
| `upload_keys` | 往项目里增加翻译 Key（可带翻译、tags） |
| `download_translations` | 导出翻译包，返回下载 URL |
| `search_keys_by_names` | 按 key 名搜索（需后端） |
| `autocomplete_keys` | Key 名前缀联想（需后端） |
| `autocomplete_tags` | Tag 联想（需后端） |

依赖后端的工具需要 `EXTENSION_BACKEND_BASE_URL` 可访问且后端已部署。
