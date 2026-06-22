# MCP Agent Toolkit

A set of **MCP (Model Context Protocol) servers**, ready to drop
into Claude Desktop, Claude Code, Cursor, Windsurf, or VS Code. Once installed,
your AI assistant can search the web, scrape websites, generate images,
drive a real browser, and publish to Notion — all from chat.

| Server | What it lets the AI do | Needs a key? |
|---|---|---|
| **Perplexity** (`server-perplexity-ask`) | Search the internet and get cited answers | ✅ `PERPLEXITY_API_KEY` |
| **Firecrawl** (`firecrawl-mcp`) | Scrape / crawl / extract structured data from any website | ✅ `FIRECRAWL_API_KEY` |
| **Glif** (`@glifxyz/glif-mcp-server`) | Generate images & run Glif AI workflows | ✅ `GLIF_API_TOKEN` |
| **Notion** (`@notionhq/notion-mcp-server`) | Read/write Notion pages & databases (e.g. publish a proposal) | ✅ `NOTION_TOKEN` |
| **Chrome DevTools** (`chrome-devtools-mcp`) | Drive & inspect a real Chrome browser (for coding agents) | ❌ |
| **Playwright** (`@playwright/mcp`) | Automate any browser — click, type, navigate, screenshot | ❌ |

Plus a curated shortlist of free REST APIs (enrichment, URL-safety, stock photos,
export) in [`recipes/extra-apis.md`](./recipes/extra-apis.md).

---

## 1. Prerequisites

- **Node.js 18+** (`node -v`) — the servers run via `npx`, no global install needed.
- **Google Chrome** installed (for the Chrome DevTools / Playwright servers).

## 2. Quick start

```bash
./scripts/setup.sh        # checks Node, creates .env, generates configs
# edit .env and paste in your keys
node scripts/generate-config.mjs   # re-generate with your keys filled in
```

Where to get each key:

- **Perplexity** → https://www.perplexity.ai/settings/api
- **Firecrawl** → https://www.firecrawl.dev/app/api-keys
- **Glif** → https://glif.app/settings/api-tokens
- **Notion** → https://www.notion.so/profile/integrations (then share the target page/database with the integration)

After `generate-config.mjs` runs, look in **`config/generated/`** for files with
your keys already filled in.

## 3. Install into your client

Pick your client, copy the config into the file below, then **restart the client**.

### Claude Desktop
Config file:
- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

Paste the contents of `config/generated/claude-cursor-windsurf.json`. If the file
already has other servers, merge the entries under the existing `"mcpServers"` key.

### Cursor
Config file: `~/.cursor/mcp.json` (global) or `.cursor/mcp.json` (per project).
Use `config/generated/claude-cursor-windsurf.json`.

### Windsurf
Config file: `~/.codeium/windsurf/mcp_config.json`.
Use `config/generated/claude-cursor-windsurf.json`.

### VS Code (GitHub Copilot)
Config file: `.vscode/mcp.json` (per project) or via **Command Palette → MCP: Add Server**.
Use `config/generated/vscode-mcp.json` (VS Code uses `"servers"` instead of `"mcpServers"`).

### Claude Code (CLI)
Run the commands in `config/generated/claude-code-cli.sh`, e.g.:

```bash
claude mcp add perplexity -e PERPLEXITY_API_KEY=your_key -- npx -y server-perplexity-ask
claude mcp add firecrawl  -e FIRECRAWL_API_KEY=your_key  -- npx -y firecrawl-mcp
claude mcp add glif        -e GLIF_API_TOKEN=your_token   -- npx -y @glifxyz/glif-mcp-server
claude mcp add chrome-devtools -- npx -y chrome-devtools-mcp@latest
claude mcp add playwright      -- npx -y @playwright/mcp@latest
```

## 4. Verify it works

Restart your client and try prompts like:

- *"Use Perplexity to find the latest news on MCP."*
- *"Use Firecrawl to scrape the pricing page at example.com and list the plans."*
- *"Use Glif to generate an image of a neon retro grid."*
- *"Use Notion to create a page titled 'Test' under my workspace."*
- *"Use Playwright to open google.com, search for 'model context protocol', and screenshot the first result."*

If a server doesn't appear, check that its key is set in `.env`, re-run
`node scripts/generate-config.mjs`, and fully restart the client.

## Recipes

Ready-made workflows that combine these servers — see [`recipes/`](./recipes/):

- [Lead generation](./recipes/lead-generation.md) — find target companies and pull contact details into a list (Perplexity + Firecrawl)
- [Sales proposal](./recipes/sales-proposal.md) — research a prospect and draft a tailored proposal (Perplexity + Firecrawl)
- [Content factory](./recipes/content-factory.md) — turn a topic into finished copy plus a matching generated image (Perplexity + Glif)
- [Auto-tests & web automation](./recipes/playwright-testing.md) — drive a real browser to test flows, then save a Playwright test (Playwright + Chrome DevTools)
- [Extra APIs](./recipes/extra-apis.md) — curated free APIs (enrichment, URL-safety, stock photos, export) that boost the recipes

## Repo layout

```
mcp-agent-toolkit/
├── config/
│   ├── mcp-servers.json          # canonical template (uses ${ENV_VARS})
│   └── generated/                # produced by generate-config.mjs (gitignored)
├── recipes/
│   ├── lead-generation.md        # Perplexity + Firecrawl
│   ├── sales-proposal.md         # Perplexity + Firecrawl
│   ├── content-factory.md        # Perplexity + Glif
│   ├── playwright-testing.md     # Playwright + Chrome DevTools
│   └── extra-apis.md             # Notion + curated free REST APIs
├── scripts/
│   ├── setup.sh                  # one-shot setup
│   └── generate-config.mjs       # fills keys → per-client config files
├── .env.example                  # copy to .env and add keys
└── README.md
```

## Notes

- **`config/generated/` and `.env` are gitignored** so your real keys never get
  committed. Share only `.env.example`.
- The toolkit pins no versions for `chrome-devtools` and `playwright` (`@latest`)
  and uses `npx -y`, so each server self-updates on launch.
