# Recipe: Auto-tests & web automation

Have the AI drive a real browser to test your site, fill forms, click through
flows, and capture screenshots — then turn what worked into a repeatable
Playwright test file.

**Servers needed:** Playwright (`@playwright/mcp`, no API key)
**Optional:** Chrome DevTools MCP for deeper inspection (network, console, perf)

**Time:** ~5–15 minutes per flow · **Output:** screenshots + a saved test script

> ✅ Only automate sites you own or are authorized to test. Respect terms of
> service and don't use this to bypass auth, captchas, or rate limits.

---

## The flow

```
1. Describe the flow to test        →  (you)
2. Drive it live in the browser     →  Playwright (navigate/click/type)
3. Assert the expected outcome      →  the AI (+ screenshots)
4. Save it as a Playwright test     →  the AI writes a .spec.ts
5. Run it headless / in CI          →  npx playwright test
```

## Step 1 — Describe the user flow

Be concrete about the steps and what "success" looks like.

```text
Use Playwright to test this flow on <https://your-site.com>:
1. Open the homepage
2. Click "Sign in"
3. Type <test@example.com> into the email field and <password> into password
4. Click the submit button
5. Expect to land on the dashboard with the text "Welcome back"
Take a screenshot at each important step and tell me where it breaks, if anywhere.
```

The Playwright MCP works from the **accessibility tree**, so you can refer to
elements by their visible label ("the Sign in button") instead of CSS selectors.

## Step 2 — Run it live and observe

Let the AI execute step by step. Useful follow-ups:

```text
- "Show me a screenshot of the current page."
- "List the visible buttons and links on this page."
- "Why did step 3 fail? Inspect the form fields."
- "Retry, but wait for the page to finish loading first."
```

If you also installed **Chrome DevTools MCP**, add:

```text
Check the browser console and network tab for errors during that flow.
```

## Step 3 — Add assertions

```text
For this flow, define clear pass/fail checks:
- URL should be /dashboard after login
- "Welcome back" text is visible
- No console errors
Report each as PASS/FAIL.
```

## Step 4 — Save it as a reusable test

```text
Convert the working flow into a Playwright test file (TypeScript) named
tests/login.spec.ts. Use accessible locators (getByRole / getByText),
web-first assertions (expect(...).toBeVisible()), and a clear test title.
Output the full file.
```

You'll get something like:

```ts
import { test, expect } from '@playwright/test';

test('user can log in and reach the dashboard', async ({ page }) => {
  await page.goto('https://your-site.com');
  await page.getByRole('button', { name: 'Sign in' }).click();
  await page.getByLabel('Email').fill('test@example.com');
  await page.getByLabel('Password').fill('password');
  await page.getByRole('button', { name: 'Submit' }).click();
  await expect(page).toHaveURL(/.*dashboard/);
  await expect(page.getByText('Welcome back')).toBeVisible();
});
```

## Step 5 — Run it yourself / in CI

```bash
npm init -y
npm install -D @playwright/test
npx playwright install        # download browsers
npx playwright test           # run headless
npx playwright test --ui      # interactive mode while developing
```

Add `npx playwright test` as a step in your CI to catch regressions on every push.

---

## Other things this recipe covers

- **Smoke test after deploy:** *"Visit these 5 key pages and confirm each loads
  without errors and shows its main heading."*
- **Form / checkout validation:** *"Try submitting the contact form with an empty
  email and confirm the validation message appears."*
- **Visual check:** *"Screenshot the pricing page at 1280px and 375px widths."*
- **Scrape-then-verify:** *"Navigate the catalog and confirm every product card
  has a price and an image."*

## Troubleshooting

| Problem | Fix |
|---|---|
| Element not found | Ask for the visible label list; the text may differ from what you expected. |
| Flaky timing | Tell it to *"wait for the network to be idle / for element X to be visible"* before acting. |
| Login blocked by captcha | Don't bypass it — use a test account/env or seed auth state instead. |
| Test passes live but fails in CI | Make sure `npx playwright install` runs in CI and the base URL is reachable. |
