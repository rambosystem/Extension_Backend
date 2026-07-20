import { createServer } from "node:http";
import { randomUUID } from "node:crypto";
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";

const LOKALISE_API_BASE_URL =
  process.env.LOKALISE_API_BASE_URL || "https://api.lokalise.com/api2";
const EXTENSION_BACKEND_BASE_URL =
  process.env.EXTENSION_BACKEND_BASE_URL || "http://43.142.250.179:8000";
const HTTP_TIMEOUT_MS = Number(process.env.MCP_HTTP_TIMEOUT_MS || 30000);

function requireLokaliseToken() {
  const token = process.env.LOKALISE_API_TOKEN;
  if (!token || !token.trim()) {
    throw new Error(
      "LOKALISE_API_TOKEN is required for this tool but is not configured."
    );
  }
  return token.trim();
}

function toToolResult(data) {
  return {
    content: [
      {
        type: "text",
        text: JSON.stringify(data, null, 2),
      },
    ],
  };
}

async function requestJson(url, { method = "GET", headers = {}, body } = {}) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), HTTP_TIMEOUT_MS);

  try {
    const response = await fetch(url, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
      signal: controller.signal,
    });

    const text = await response.text();
    let data = null;

    if (text) {
      try {
        data = JSON.parse(text);
      } catch {
        data = { raw: text };
      }
    }

    if (!response.ok) {
      const message =
        data?.error?.message ||
        data?.message ||
        `HTTP ${response.status} ${response.statusText}`;
      throw new Error(message);
    }

    return data;
  } finally {
    clearTimeout(timeout);
  }
}

function normalizeKeysForUpload(keys, tags) {
  return keys.map((key) => {
    const normalized = {
      key_name: key.key_name,
      platforms: Array.isArray(key.platforms) ? key.platforms : ["web", "other"],
      translations: Array.isArray(key.translations) ? key.translations : [],
    };

    if (Array.isArray(key.tags) && key.tags.length > 0) {
      normalized.tags = key.tags;
    } else if (Array.isArray(tags) && tags.length > 0) {
      normalized.tags = tags;
    }

    return normalized;
  });
}

const tools = [
  {
    name: "list_projects",
    description: "List Lokalise projects for the configured API token.",
    inputSchema: {
      type: "object",
      properties: {},
      additionalProperties: false,
    },
  },
  {
    name: "upload_keys",
    description: "Upload translation keys into a Lokalise project.",
    inputSchema: {
      type: "object",
      properties: {
        project_id: { type: "string", minLength: 1 },
        keys: {
          type: "array",
          minItems: 1,
          items: {
            type: "object",
            properties: {
              key_name: { type: "string", minLength: 1 },
              platforms: {
                type: "array",
                items: { type: "string" },
              },
              translations: {
                type: "array",
                items: {
                  type: "object",
                  properties: {
                    language_iso: { type: "string", minLength: 1 },
                    translation: { type: "string" },
                  },
                  required: ["language_iso", "translation"],
                  additionalProperties: true,
                },
              },
              tags: {
                type: "array",
                items: { type: "string" },
              },
            },
            required: ["key_name", "translations"],
            additionalProperties: true,
          },
        },
        tags: {
          type: "array",
          items: { type: "string" },
        },
      },
      required: ["project_id", "keys"],
      additionalProperties: false,
    },
  },
  {
    name: "search_keys_by_names",
    description:
      "Search key names by calling backend /lokalise/search-by-names endpoint.",
    inputSchema: {
      type: "object",
      properties: {
        project_id: { type: "string", minLength: 1 },
        key_names: {
          type: "array",
          minItems: 1,
          items: { type: "string", minLength: 1 },
        },
      },
      required: ["project_id", "key_names"],
      additionalProperties: false,
    },
  },
  {
    name: "autocomplete_tags",
    description:
      "Autocomplete tags by calling backend /lokalise/autocomplete/tags.",
    inputSchema: {
      type: "object",
      properties: {
        project_id: { type: "string", minLength: 1 },
        query: { type: "string" },
        limit: { type: "integer", minimum: 1, maximum: 50, default: 5 },
      },
      required: ["project_id", "query"],
      additionalProperties: false,
    },
  },
  {
    name: "autocomplete_keys",
    description:
      "Autocomplete translation key names by prefix (backend). Use when user is typing a key name to suggest existing keys (single-word keys only).",
    inputSchema: {
      type: "object",
      properties: {
        project_id: { type: "string", minLength: 1 },
        query: { type: "string", minLength: 1 },
        limit: { type: "integer", minimum: 1, maximum: 20, default: 5 },
      },
      required: ["project_id", "query"],
      additionalProperties: false,
    },
  },
  {
    name: "list_languages",
    description:
      "List languages (locales) for a Lokalise project. Use to know which language_iso values exist for upload_keys or download.",
    inputSchema: {
      type: "object",
      properties: {
        project_id: { type: "string", minLength: 1 },
      },
      required: ["project_id"],
      additionalProperties: false,
    },
  },
  {
    name: "download_translations",
    description:
      "Export project translations as a zip bundle from Lokalise. Returns a download URL (valid ~1 month). Use for frontend: get translation files (e.g. en.json, zh.json) to use in the app.",
    inputSchema: {
      type: "object",
      properties: {
        project_id: { type: "string", minLength: 1 },
        format: {
          type: "string",
          enum: ["json", "json_nested", "ios_strings", "android_xml", "properties", "po", "xlsx", "csv"],
          default: "json",
        },
        original_filenames: {
          type: "boolean",
          default: false,
          description: "If true, use filenames from Lokalise; if false, one file per language.",
        },
        lang_iso: {
          type: "array",
          items: { type: "string" },
          description: "Optional: export only these language codes (e.g. ['en', 'zh']). Omit for all languages.",
        },
      },
      required: ["project_id"],
      additionalProperties: false,
    },
  },
];

const server = new Server(
  {
    name: "mcp-lokalise",
    version: "0.1.0",
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({ tools }));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args = {} } = request.params;

  if (name === "list_projects") {
    const token = requireLokaliseToken();
    const data = await requestJson(`${LOKALISE_API_BASE_URL}/projects`, {
      method: "GET",
      headers: {
        "X-Api-Token": token,
        "Content-Type": "application/json",
      },
    });

    const projects = Array.isArray(data?.projects) ? data.projects : [];
    return toToolResult({
      count: projects.length,
      projects: projects.map((project) => ({
        project_id: project?.project_id,
        name: project?.name,
      })),
    });
  }

  if (name === "upload_keys") {
    const token = requireLokaliseToken();
    const projectId = String(args.project_id || "").trim();
    const keys = Array.isArray(args.keys) ? args.keys : [];
    const tags = Array.isArray(args.tags) ? args.tags : [];

    if (!projectId) {
      throw new Error("project_id is required.");
    }
    if (keys.length === 0) {
      throw new Error("keys must be a non-empty array.");
    }

    const body = {
      keys: normalizeKeysForUpload(keys, tags),
    };

    const data = await requestJson(
      `${LOKALISE_API_BASE_URL}/projects/${projectId}/keys`,
      {
        method: "POST",
        headers: {
          "X-Api-Token": token,
          "Content-Type": "application/json",
        },
        body,
      }
    );

    return toToolResult(data);
  }

  if (name === "search_keys_by_names") {
    const projectId = String(args.project_id || "").trim();
    const keyNames = Array.isArray(args.key_names) ? args.key_names : [];

    if (!projectId) {
      throw new Error("project_id is required.");
    }
    if (keyNames.length === 0) {
      throw new Error("key_names must be a non-empty array.");
    }

    const data = await requestJson(
      `${EXTENSION_BACKEND_BASE_URL}/lokalise/search-by-names`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: {
          project_id: projectId,
          key_names: keyNames,
        },
      }
    );

    return toToolResult(data);
  }

  if (name === "autocomplete_tags") {
    const projectId = String(args.project_id || "").trim();
    const query = String(args.query || "");
    const limit = Number.isInteger(args.limit) ? args.limit : 5;

    if (!projectId) {
      throw new Error("project_id is required.");
    }

    const url = new URL(
      `${EXTENSION_BACKEND_BASE_URL}/lokalise/autocomplete/tags`
    );
    url.searchParams.set("project_id", projectId);
    url.searchParams.set("query", query);
    url.searchParams.set("limit", String(limit));

    const data = await requestJson(url.toString(), {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    });

    return toToolResult(data);
  }

  if (name === "autocomplete_keys") {
    const projectId = String(args.project_id || "").trim();
    const query = String(args.query || "").trim();
    const limit = Number.isInteger(args.limit) ? Math.min(args.limit, 20) : 5;

    if (!projectId) {
      throw new Error("project_id is required.");
    }
    if (!query) {
      throw new Error("query is required for autocomplete_keys.");
    }

    const url = new URL(
      `${EXTENSION_BACKEND_BASE_URL}/lokalise/autocomplete/keys`
    );
    url.searchParams.set("project_id", projectId);
    url.searchParams.set("query", query);
    url.searchParams.set("limit", String(limit));

    const data = await requestJson(url.toString(), {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });

    return toToolResult(data);
  }

  if (name === "list_languages") {
    const token = requireLokaliseToken();
    const projectId = String(args.project_id || "").trim();
    if (!projectId) {
      throw new Error("project_id is required.");
    }

    const data = await requestJson(
      `${LOKALISE_API_BASE_URL}/projects/${projectId}/languages`,
      {
        method: "GET",
        headers: {
          "X-Api-Token": token,
          "Content-Type": "application/json",
        },
      }
    );

    const languages = Array.isArray(data?.languages) ? data.languages : [];
    return toToolResult({
      count: languages.length,
      languages: languages.map((lang) => ({
        lang_iso: lang?.lang_iso,
        lang_name: lang?.lang_name,
      })),
    });
  }

  if (name === "download_translations") {
    const token = requireLokaliseToken();
    const projectId = String(args.project_id || "").trim();
    const format = String(args.format || "json").toLowerCase();
    const originalFilenames = Boolean(args.original_filenames);
    const langIso = Array.isArray(args.lang_iso)
      ? args.lang_iso.filter((s) => typeof s === "string" && s.trim())
      : undefined;

    if (!projectId) {
      throw new Error("project_id is required.");
    }

    const body = {
      format,
      original_filenames: originalFilenames,
    };
    if (langIso && langIso.length > 0) {
      body.lang_iso = langIso;
    }

    const data = await requestJson(
      `${LOKALISE_API_BASE_URL}/projects/${projectId}/files/download`,
      {
        method: "POST",
        headers: {
          "X-Api-Token": token,
          "Content-Type": "application/json",
        },
        body,
      }
    );

    return toToolResult({
      bundle_url: data?.bundle_url ?? data?.url,
      message:
        "Download URL valid for about 1 month. Use bundle_url to fetch the zip of translation files.",
      ...data,
    });
  }

  throw new Error(`Unknown tool: ${name}`);
});

const MCP_HTTP_PORT = process.env.MCP_HTTP_PORT
  ? Number(process.env.MCP_HTTP_PORT)
  : 0;
const MCP_HTTP_PATH = process.env.MCP_HTTP_PATH || "/sse";

function readBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    req.on("data", (chunk) => chunks.push(chunk));
    req.on("end", () => {
      const raw = Buffer.concat(chunks).toString("utf8");
      if (!raw.trim()) {
        resolve(undefined);
        return;
      }
      try {
        resolve(JSON.parse(raw));
      } catch (e) {
        reject(e);
      }
    });
    req.on("error", reject);
  });
}

async function main() {
  if (MCP_HTTP_PORT > 0) {
    const transport = new StreamableHTTPServerTransport({
      sessionIdGenerator: () => randomUUID(),
    });
    await server.connect(transport);

    const httpServer = createServer(async (req, res) => {
      const path = req.url?.split("?")[0] || "";
      if (path !== MCP_HTTP_PATH) {
        res.statusCode = 404;
        res.setHeader("Content-Type", "application/json");
        res.end(JSON.stringify({ error: "Not Found", path: MCP_HTTP_PATH }));
        return;
      }
      let parsedBody;
      if (req.method === "POST") {
        try {
          parsedBody = await readBody(req);
        } catch (e) {
          res.statusCode = 400;
          res.setHeader("Content-Type", "application/json");
          res.end(JSON.stringify({ error: "Invalid JSON body" }));
          return;
        }
      }
      try {
        await transport.handleRequest(req, res, parsedBody);
      } catch (err) {
        console.error("[mcp-lokalise] handleRequest error:", err);
        if (!res.headersSent) {
          res.statusCode = 500;
          res.setHeader("Content-Type", "application/json");
          res.end(JSON.stringify({ error: String(err?.message || err) }));
        }
      }
    });

    httpServer.listen(MCP_HTTP_PORT, "0.0.0.0", () => {
      console.error(
        `[mcp-lokalise] HTTP MCP server listening on http://0.0.0.0:${MCP_HTTP_PORT}${MCP_HTTP_PATH}`
      );
    });
    return;
  }

  const transport = new StdioServerTransport();
  await server.connect(transport);
}

main().catch((error) => {
  console.error("[mcp-lokalise] Failed to start:", error);
  process.exit(1);
});
