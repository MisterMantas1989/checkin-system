# Recipe: Extra APIs that supercharge the agent

A curated shortlist from the [public-apis](https://github.com/public-apis/public-apis)
mega-list — the ones that actually add value to *this* toolkit and its recipes.

Most of these are **plain REST APIs**, not MCP servers. The agent uses them in
one of two ways:

- **Via the browser/scraper servers** — ask the agent to call a public endpoint
  with Firecrawl/Playwright, or to fetch a documented URL.
- **Wrapped as a tiny MCP server** — only worth it for ones you use constantly.

> Notion is the exception: it has an **official MCP server** and is already wired
> into `config/mcp-servers.json`. See the [sales-proposal recipe](./sales-proposal.md).

---

## Lead generation & B2B enrichment
Pairs with the [lead-generation recipe](./lead-generation.md).

| API | Use | Auth | Notes |
|---|---|---|---|
| **VATlayer** | Validate EU VAT numbers (verify a business is real) | API key | Great for Swedish/EU B2B leads |
| **Clearbit Logo** | Fetch a company's logo by domain | API key (free tier) | `logo.clearbit.com/<domain>` |
| **ipapi / ipstack** | Geocode / locate by IP or domain | API key | Enrich leads with country/city |
| **Abstract / Hunter-style email tools** | Find & verify business emails | API key | Check each provider's ToS |

**Prompt idea:**
> *"For each lead, validate its VAT number with VATlayer and fetch its logo via
> Clearbit. Drop invalid companies and add a `logo_url` column."*

## URL & scrape safety
Run these **before** Firecrawl/Playwright visit an unknown site — pairs with the
[auto-test recipe](./playwright-testing.md).

| API | Use | Auth |
|---|---|---|
| **Google Safe Browsing** | Is this URL flagged as malware/phishing? | API key |
| **URLScan.io** | Scan & screenshot a URL safely | API key |
| **AbuseIPDB** | Reputation check on an IP/host | API key |

**Prompt idea:**
> *"Before scraping these URLs, check each one with Google Safe Browsing and skip
> any that come back unsafe."*

## Content & media
Pairs with the [content-factory recipe](./content-factory.md) as an alternative
to Glif when you need *real* photos.

| API | Use | Auth | Notes |
|---|---|---|---|
| **Unsplash** | Free high-res stock photos | API key | Attribution required |
| **Pexels** | Free stock photos & video | API key | Generous free tier |
| **Pixabay** | Free images, vectors, video | API key | |
| **OCR.Space** | Extract text from images/PDFs | API key | Repurpose text from screenshots |

**Prompt idea:**
> *"If a generated Glif image doesn't fit, search Unsplash for a matching photo
> and return the URL plus the required attribution."*

## Output & export
Turn agent output into shareable documents.

| API / Server | Use | Auth | Notes |
|---|---|---|---|
| **Notion** ⭐ | Publish pages/databases | Integration token | **Official MCP server — already configured** |
| **CloudConvert** | Convert Markdown → PDF/DOCX | API key | Export a finished proposal |
| **Google Sheets** | Write leads/results to a sheet | OAuth | Good target for lead lists |

## Prospect research (finance)
Pairs with the [sales-proposal recipe](./sales-proposal.md) for public companies.

| API | Use | Auth |
|---|---|---|
| **Alpha Vantage** | Stock/financial data | API key (free) |
| **Finnhub** | Company financials, news, filings | API key (free tier) |

**Prompt idea:**
> *"If the prospect is publicly traded, pull recent financials from Finnhub and
> work the relevant numbers into the proposal's ROI section."*

---

## How to wire a raw REST API into the agent

For anything without an MCP server, the simplest path is to tell the agent the
endpoint and let it call it through the scraping/browser servers, e.g.:

> *"Call `https://api.vatlayer.com/validate?access_key=KEY&vat_number=SE556...`
> and tell me whether the VAT number is valid."*

If you find yourself using one constantly, wrap it as a small MCP server (the
[MCP SDK](https://modelcontextprotocol.io) makes this ~30 lines) and add it to
`config/mcp-servers.json` alongside the others.

> ⚖️ Respect each API's terms, rate limits, and attribution requirements, and
> follow privacy law (GDPR) when handling personal data.
