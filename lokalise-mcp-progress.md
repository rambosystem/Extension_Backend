# Lokalise MCP 服务扩展进度

## 目标
实现 Lokalise MCP 服务，覆盖前端（Edge Extension）常用能力：**翻译**（获取翻译文件/内容）、**增加翻译 Key**。

## 现状
- **后端**：已有完整 Lokalise 集成（webhook 同步 keys/tags、`/lokalise/keys`、`/search-by-names`、`/autocomplete/keys`、`/autocomplete/tags`）。
- **MCP**（`mcp/lokalise`）：已有 `list_projects`、`upload_keys`、`search_keys_by_names`、`autocomplete_tags`。

## 已做改动
1. **MCP 新增 3 个工具**（`mcp/lokalise/src/index.js`）：
   - `autocomplete_keys`：调后端 `GET /lokalise/autocomplete/keys`，按前缀推荐 key 名（前端输入联想）。
   - `list_languages`：调 Lokalise API `GET /projects/{id}/languages`，列出项目语言，便于上传/下载时使用 `language_iso`。
   - `download_translations`：调 Lokalise API `POST /projects/{id}/files/download`，导出翻译 zip，返回下载 URL（约 1 个月有效），供前端拉取 en.json、zh.json 等。
2. **README**：更新工具列表与说明；注明 token/backend 依赖及前端使用方式。

## 可行性结论
**好实现。** 增加 Key 已有 `upload_keys`；翻译侧用 Lokalise 官方 download 接口即可拿到翻译包，前端用返回的 URL 下载即可。MCP 仅需透传后端与 Lokalise API，无需在前端项目（E:\Edge_Extension）重复实现逻辑。

## 使用方式（前端/IDE）
- 加新 Key：`upload_keys`（project_id, keys[]，可选 tags、translations）。
- 获取翻译文件：`download_translations`（project_id, format, original_filenames, 可选 lang_iso[]）→ 用返回的 `bundle_url` 下载 zip。
- Key/Tag 联想：`autocomplete_keys`、`autocomplete_tags`（需后端运行且配置 `EXTENSION_BACKEND_BASE_URL`）。

## 在 Cursor 里用（含 E:\Workspace\Jira）
- **推荐**：与 mcp-atlassian 同一种方式——**command + args + env**。在 `~/.cursor/mcp.json` 里增加 `mcp-lokalise`，`command` 填 `node`，`args` 填本机 `mcp/lokalise/src/index.js` 的绝对路径，`env` 填 `LOKALISE_API_TOKEN`、`EXTENSION_BACKEND_BASE_URL`。若本机没有仓库，可只拷 `mcp/lokalise` 目录并执行 `npm install`。示例见 `docs/CURSOR_MCP_SETUP.md` 与 `mcp/lokalise/cursor-mcp-example.json`。
- 备选：服务器起 HTTP 模式（`MCP_HTTP_PORT=3100`），本机用 `"url": "http://服务器:3100/sse"` 连接。
- 若在服务器上直接打开 extension_backend 用 Cursor：用仓库内 `.cursor/mcp.json`（stdio）即可。

## 环境变量
- `LOKALISE_API_TOKEN`：list_projects、upload_keys、list_languages、download_translations 必需。
- `EXTENSION_BACKEND_BASE_URL`：search_keys_by_names、autocomplete_* 需指向当前后端。
