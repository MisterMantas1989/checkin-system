# Recipe: Lead generation

Find companies that match a target profile and assemble a clean list of leads
with contact details — the kind of workflow shown in the reference video.

**Servers needed:** Perplexity (`PERPLEXITY_API_KEY`), Firecrawl (`FIRECRAWL_API_KEY`)

**Time:** ~5–10 minutes per batch · **Output:** a CSV/table of qualified leads

> ⚖️ Use responsibly. Only collect publicly available business contact info,
> respect each site's terms and `robots.txt`, and follow GDPR / local privacy law
> (especially when handling personal data of EU residents). This is for legitimate
> B2B outreach, not scraping personal data at scale.

---

## The flow

```
1. Define the target profile        →  (you)
2. Discover candidate companies      →  Perplexity (web search)
3. Scrape each site for details      →  Firecrawl (extract)
4. Enrich + dedupe into a table      →  the AI
5. Export as CSV                     →  the AI
```

## Step 1 — Define your ideal customer profile (ICP)

Be specific. Vague input → vague leads.

```text
I'm doing B2B lead generation. My ideal customer profile:
- Industry: <e.g. SaaS companies selling HR software>
- Location: <e.g. Sweden, Stockholm area>
- Size: <e.g. 10–200 employees>
- Signal: <e.g. recently raised funding, or hiring salespeople>
Keep this profile in mind for the next steps.
```

## Step 2 — Discover candidate companies (Perplexity)

```text
Use Perplexity to find 15–20 companies matching that profile.
For each, return: company name, website URL, and a one-line reason it fits.
Prefer recent sources and include the source links.
```

If you need more, ask: *"Find 15 more, excluding the ones already listed."*

## Step 3 — Scrape each company for contact details (Firecrawl)

```text
For each company website, use Firecrawl to find and extract:
- company name
- website
- a contact or "about" email (e.g. info@, sales@) if publicly listed
- the founder/CEO name and their public email if shown on the site
- LinkedIn or contact page URL
- city / HQ location
Visit the homepage plus likely pages (/contact, /about, /team).
If a field isn't publicly available, leave it blank — do not guess.
```

## Step 4 — Enrich, dedupe, and qualify

```text
Combine everything into a single table. Remove duplicates.
Add a "fit score" 1–5 based on how well each matches my ICP, with a short note.
Sort by fit score (highest first).
```

## Step 5 — Export

```text
Output the final list as CSV with these columns:
company, website, contact_email, ceo_name, ceo_email, linkedin, city, fit_score, notes
```

Then save it: paste into a spreadsheet, or ask your AI client to write it to a
`leads.csv` file if it has filesystem access.

---

## Variations

- **Add a personalized opener:** *"For each lead, draft a one-sentence, specific
  cold-email opener referencing something real from their website."*
- **Tighter targeting:** add signals like *"only companies whose site mentions
  they're hiring"* — Firecrawl can check the careers page.
- **Bigger batches:** run Steps 2–4 in rounds of 20 to stay accurate; quality
  drops if you ask for 100 at once.

## Troubleshooting

| Problem | Fix |
|---|---|
| Firecrawl returns empty fields | The data may not be public — that's expected; don't let the AI invent it. |
| Same companies repeat | Add *"excluding: <list>"* to the discovery prompt. |
| Rate limited | Slow down; process fewer sites per request. |
| Results feel generic | Make the ICP in Step 1 much more specific. |
