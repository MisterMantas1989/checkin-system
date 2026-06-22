#!/usr/bin/env node
// Reads ./.env and ./config/mcp-servers.json, then writes ready-to-paste
// config files (with your keys substituted) into ./config/generated/ for
// Claude Desktop / Cursor / Windsurf, VS Code, and Claude Code CLI commands.

import { readFileSync, writeFileSync, mkdirSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const outDir = join(root, "config", "generated");

// --- load .env (simple parser, no deps) ---
const env = {};
const envPath = join(root, ".env");
if (existsSync(envPath)) {
  for (const line of readFileSync(envPath, "utf8").split("\n")) {
    const m = line.match(/^\s*([A-Z0-9_]+)\s*=\s*(.*)\s*$/);
    if (m) env[m[1]] = m[2].replace(/^["']|["']$/g, "");
  }
} else {
  console.warn("⚠  No .env found — keys will be left blank. Run: cp .env.example .env");
}

// --- load the canonical template and substitute ${VARS} ---
const tpl = readFileSync(join(root, "config", "mcp-servers.json"), "utf8");
const filled = tpl.replace(/\$\{([A-Z0-9_]+)\}/g, (_, k) => env[k] ?? "");
const base = JSON.parse(filled);

mkdirSync(outDir, { recursive: true });

// Claude Desktop / Cursor / Windsurf all use the `mcpServers` shape.
writeFileSync(join(outDir, "claude-cursor-windsurf.json"), JSON.stringify(base, null, 2) + "\n");

// VS Code (Copilot) uses `servers` instead of `mcpServers`.
writeFileSync(join(outDir, "vscode-mcp.json"), JSON.stringify({ servers: base.mcpServers }, null, 2) + "\n");

// Claude Code CLI: emit `claude mcp add` commands.
const lines = ["#!/usr/bin/env bash", "set -euo pipefail", ""];
for (const [name, cfg] of Object.entries(base.mcpServers)) {
  const envFlags = Object.entries(cfg.env ?? {}).map(([k, v]) => `-e ${k}=${v || "<set-me>"}`).join(" ");
  const cmd = [cfg.command, ...cfg.args].join(" ");
  lines.push(`claude mcp add ${name} ${envFlags ? envFlags + " " : ""}-- ${cmd}`);
}
writeFileSync(join(outDir, "claude-code-cli.sh"), lines.join("\n") + "\n");

const missing = Object.entries({
  PERPLEXITY_API_KEY: "perplexity",
  FIRECRAWL_API_KEY: "firecrawl",
  GLIF_API_TOKEN: "glif",
}).filter(([k]) => !env[k]).map(([, s]) => s);

console.log("✓ Wrote config/generated/{claude-cursor-windsurf.json, vscode-mcp.json, claude-code-cli.sh}");
if (missing.length) console.log(`⚠  No key set for: ${missing.join(", ")} (those servers won't start until you add keys to .env)`);
