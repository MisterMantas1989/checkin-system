# Recipe: Content factory

Go from a topic to a finished content piece — researched copy **plus** a matching
generated image — in one chat. Great for social posts, blog articles, and
newsletters.

**Servers needed:** Glif (`GLIF_API_TOKEN`)
**Recommended:** Perplexity (`PERPLEXITY_API_KEY`) for up-to-date, sourced research

**Time:** ~5 minutes per piece · **Output:** caption/article + a generated image

---

## The flow

```
1. Pick the topic + format + audience   →  (you)
2. Research the angle                     →  Perplexity (web search)
3. Write the copy                         →  the AI
4. Generate a matching image              →  Glif
5. Package for the channel                →  the AI
```

## Step 1 — Brief the piece

```text
I'm creating content. Brief:
- Topic: <e.g. why small teams should adopt MCP servers>
- Format: <e.g. LinkedIn post / blog intro / newsletter blurb / X thread>
- Audience: <e.g. startup founders>
- Brand voice: <e.g. practical, confident, no hype>
- Goal: <e.g. drive sign-ups to our newsletter>
Hold this brief for the next steps.
```

## Step 2 — Research the angle (Perplexity)

```text
Use Perplexity to find 5–6 fresh, specific facts, stats, or examples that would
make this piece credible and interesting. Include source links. Skip generic
points everyone already knows.
```

## Step 3 — Write the copy

```text
Write the <format> based on the brief and research.
- Open with a strong hook.
- Use 1–2 of the researched facts naturally (no fact-dumping).
- Keep the brand voice. End with a clear CTA toward my goal.
- Give me 3 headline/hook options at the top to choose from.
```

## Step 4 — Generate a matching image (Glif)

First, see what's available, then generate:

```text
Use Glif to generate an image to accompany this post.
Style: <e.g. clean flat illustration / bold 3D render / retro neon>.
Subject: <describe the visual concept that fits the copy>.
Aspect ratio: <e.g. 1:1 for Instagram, 16:9 for blog header, 1.91:1 for LinkedIn>.
Show me the result and the prompt you used so I can tweak it.
```

> Glif also hosts many community "glifs" (prebuilt workflows: memes, logos,
> styled templates). Ask: *"List relevant Glif workflows for <use case> and run
> the best fit"* to use a specialized one instead of raw image generation.

**Need a real photo instead of a generated one?** Use a free stock API
(Unsplash / Pexels / Pixabay) — see [extra-apis.md](./extra-apis.md):

```text
If a generated image doesn't fit, search Unsplash for a photo matching this post
and return the image URL plus the required attribution.
```

## Step 5 — Package for the channel

```text
Assemble the final deliverable:
- The chosen headline + body copy, formatted for <channel>
- 5–8 relevant hashtags (if social)
- A 1-line alt text for the image (accessibility)
- A suggested posting time/notes
```

---

## Batch mode (a week of content)

```text
Using the same brief and voice, produce 5 posts on these subtopics: <list>.
For each: hook + body + one Glif image prompt + hashtags.
Output as a table so I can schedule them.
```

Then generate the images one by one (*"now generate the image for post 3"*) to
keep quality high.

## Variations

- **Repurpose:** *"Turn this blog post into a 5-tweet thread and an Instagram
  caption, each with its own Glif image."*
- **On-brand visuals:** describe your brand colors/style every time, or save a
  reusable style block in Step 4.
- **Carousel:** *"Generate 4 images for a carousel that tell a sequence."*

## Tips

- Generate images **after** the copy is locked so the visual matches the message.
- Always keep the Glif prompt the AI used — small wording tweaks change the
  result a lot.
- Check image rights/usage terms for your plan before publishing commercially.
- If an image misses, refine the prompt ("more minimal", "darker background",
  "no text") rather than regenerating blindly.
