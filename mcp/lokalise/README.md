# mcp-lokalise

Standalone MCP server for Lokalise and extension backend APIs. Supports **translation** (export/download) and **adding translation keys** for frontend workflows (e.g. Edge Extension).

## Tools

| Tool | Description |
|------|-------------|
| `list_projects` | List Lokalise projects for the configured token. |
| `list_languages` | List languages (locales) for a project; use for `language_iso` in upload/download. |
| `upload_keys` | Upload translation keys (and optional translations) to a Lokalise project. |
| `download_translations` | Export project as zip; returns download URL. Use to get translation files (e.g. en.json, zh.json) for frontend. |
| `search_keys_by_names` | Call backend `/lokalise/search-by-names` to find keys by name. |
| `autocomplete_keys` | Call backend `/lokalise/autocomplete/keys`; suggest key names by prefix (for UI). |
| `autocomplete_tags` | Call backend `/lokalise/autocomplete/tags`. |

## Setup

1. Copy `.env.example` and set values in your runtime environment.
2. Install dependencies:

```bash
npm install
```

3. Run MCP server:

**Stdio** (e.g. Cursor spawns it locally):

```bash
npm start
```

**HTTP** (remote MCP server; Cursor connects via URL):

```bash
MCP_HTTP_PORT=3100 npm run start:http
```

Then in Cursor `mcp.json` use `"url": "http://your-server:3100/sse"` (no local copy needed).

**Cursor command mode** (same style as mcp-atlassian: `command` + `args` + `env`): see `cursor-mcp-example.json` and `docs/CURSOR_MCP_SETUP.md`. Use `command: "node"`, `args: ["/absolute/path/to/mcp/lokalise/src/index.js"]`, and `env` for `LOKALISE_API_TOKEN` and `EXTENSION_BACKEND_BASE_URL`.

## Notes

- `LOKALISE_API_TOKEN`: required for `list_projects`, `upload_keys`, `list_languages`, `download_translations`.
- `EXTENSION_BACKEND_BASE_URL`: used for `search_keys_by_names`, `autocomplete_tags`, `autocomplete_keys` (backend must be running).
- Frontend use: use `upload_keys` to add new keys; use `download_translations` to get translation file URLs; use `autocomplete_keys` / `autocomplete_tags` for key/tag suggestions in UI.
