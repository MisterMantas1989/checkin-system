# Recipe: Sales proposal

Research a prospect and turn that research into a tailored, ready-to-send sales
proposal — the workflow demonstrated at the end of the reference video.

**Servers needed:** Perplexity (`PERPLEXITY_API_KEY`), Firecrawl (`FIRECRAWL_API_KEY`)
**Optional:** Notion (`NOTION_TOKEN`, already in `config/mcp-servers.json`) to publish the final document.

**Time:** ~10 minutes · **Output:** a structured proposal you can edit and send

---

## The flow

```
1. Set the context (who you are, what you sell)   →  (you)
2. Research the prospect                            →  Perplexity + Firecrawl
3. Identify pain points & angle                     →  the AI
4. Draft the proposal                               →  the AI
5. Polish + export                                  →  the AI (+ Docs/Notion MCP)
```

## Step 1 — Set the context

```text
I'm preparing a sales proposal. Context:
- My company: <what you do, in one line>
- What I'm selling: <product/service + the core outcome it delivers>
- Pricing model: <e.g. €2k setup + €500/mo, or 3 tiers>
- The prospect: <company name + website>
- My goal with this proposal: <e.g. book a pilot, close a retainer>
Hold this context for the next steps.
```

## Step 2 — Research the prospect (Perplexity + Firecrawl)

```text
Research <prospect company>:
1. Use Firecrawl to read their website (homepage, product, about, pricing,
   careers) and summarize what they do, who they serve, and how they make money.
2. Use Perplexity to find recent news: funding, launches, hiring, leadership,
   and any public challenges or goals. Include source links.
Give me a tight briefing of the 8–10 most relevant facts.
```

## Step 3 — Find the angle

```text
Based on that research, identify:
- 3 likely pain points or goals this company has right now
- For each, exactly how <my product/service> helps, with a concrete outcome
- The single strongest angle to lead the proposal with
Be specific to THIS company — no generic filler.
```

## Step 4 — Draft the proposal

```text
Write a sales proposal for <prospect> using this structure:

1. Title + one-line value proposition tailored to them
2. Executive summary (3–4 sentences)
3. Their situation / challenges (shows we did our homework — cite the research)
4. Proposed solution (map our offering to their specific pain points)
5. What's included + timeline / phases
6. Investment & ROI (use my pricing model; show expected return)
7. Why us (2–3 proof points)
8. Clear next step / call to action

Tone: confident, concise, specific. No fluff. Use their name and real details
throughout.
```

## Step 5 — Polish and export

```text
- Tighten any vague sentences and remove repetition.
- Make sure every claim ties back to the research.
- Output as clean Markdown I can drop into a doc.
```

**Publish it to Notion** (the Notion MCP server is already configured):

```text
Use Notion to create a new page titled "<Prospect> — Proposal" under <my
proposals page/database>, with the proposal content formatted as headings,
paragraphs and a pricing table. Share the page URL.
```

> First time: create a Notion integration at
> https://www.notion.so/profile/integrations, put its token in `.env` as
> `NOTION_TOKEN`, and **share the target page/database with the integration**
> inside Notion (⋯ menu → Connections) — otherwise the agent can't see it.
>
> Prefer a PDF/Word file instead? See **CloudConvert** in
> [extra-apis.md](./extra-apis.md).

---

## Variations

- **One-pager vs full deck:** *"Condense this into a single-page proposal"* or
  *"expand section 4 into a detailed scope of work."*
- **Multiple prospects:** rerun Steps 2–4 per company; keep Step 1 context fixed.
- **Localized:** *"Write the proposal in Swedish, formal business tone."*
- **Follow-up email:** *"Now write a short email to send with this proposal."*

## Tips

- The quality of the proposal is only as good as Step 2's research — don't skip it.
- Always review pricing and claims yourself before sending; the AI can misread
  details from a website.
- Keep a reusable "Step 1 context" block saved so you only edit the prospect line.
