# Recipes

Copy-paste workflows that combine the MCP servers in this toolkit. Each recipe
lists the servers it needs, a step-by-step flow, and ready-to-use prompts you
can paste straight into your AI client.

| Recipe | What it does | Servers used |
|---|---|---|
| [Lead generation](./lead-generation.md) | Find target companies and pull contact details into a clean list | Perplexity + Firecrawl |
| [Sales proposal](./sales-proposal.md) | Research a prospect and draft a tailored sales proposal | Perplexity + Firecrawl |
| [Content factory](./content-factory.md) | Turn a topic into finished copy plus a matching generated image | Perplexity + Glif |

## How to use a recipe

1. Make sure the recipe's servers are installed and your keys are in `.env`
   (see the main [README](../README.md)).
2. Open a fresh chat in your AI client.
3. Paste the prompts from the recipe in order, editing the **`<>` placeholders**
   for your own target.
4. Iterate — these are starting points, not magic buttons. Refine the output by
   asking follow-up questions.

> Tip: keep each recipe in its own chat so the AI's context stays focused.
