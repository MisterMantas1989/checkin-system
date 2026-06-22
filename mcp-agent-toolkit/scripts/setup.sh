#!/usr/bin/env bash
# Quick setup for the MCP Agent Toolkit.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "▶ Checking prerequisites…"
command -v node >/dev/null || { echo "✗ Node.js not found. Install Node 18+ from https://nodejs.org"; exit 1; }
command -v npx  >/dev/null || { echo "✗ npx not found (comes with npm)."; exit 1; }
node_major=$(node -p "process.versions.node.split('.')[0]")
[ "$node_major" -ge 18 ] || { echo "✗ Node 18+ required (found $(node -v))."; exit 1; }
echo "  Node $(node -v) ✓"

if [ ! -f .env ]; then
  cp .env.example .env
  echo "▶ Created .env from .env.example — now open it and add your API keys."
else
  echo "▶ .env already exists — leaving it as is."
fi

echo "▶ Pre-caching MCP server packages (so first launch is fast)…"
for pkg in server-perplexity-ask firecrawl-mcp @glifxyz/glif-mcp-server @notionhq/notion-mcp-server chrome-devtools-mcp @playwright/mcp; do
  echo "  • $pkg"
  npm view "$pkg" version >/dev/null 2>&1 || echo "    (could not reach npm for $pkg — skipping)"
done

echo "▶ Generating ready-to-paste client configs…"
node scripts/generate-config.mjs

cat <<'EOF'

✅ Done. Next steps:
   1. Edit .env and paste in your keys (Perplexity / Firecrawl / Glif / Notion).
   2. Re-run:  node scripts/generate-config.mjs
   3. Copy the right file from config/generated/ into your AI client
      (see the README for exact paths), then restart the client.
EOF
