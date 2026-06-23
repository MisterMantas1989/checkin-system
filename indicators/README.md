# Smart Trade Setup — TradingView Indicator

A Pine Script (v6) indicator that recreates the trade-setup tool shown in the
reference video. Add it to any TradingView chart as an **overlay**.

File: [`smart_trade_setup.pine`](./smart_trade_setup.pine)

## What it draws

The indicator reproduces the elements demonstrated in the clip, on any symbol
and timeframe:

| Element | In the video | In the indicator |
| --- | --- | --- |
| Market structure | swing highs/lows | pivot detection (`Swing strength`) |
| Order blocks | grey boxes at swing tips | supply/demand boxes (`Order blocks`) |
| Support / Resistance | red horizontal line + "Resistance" | line + label at the active level |
| Fibonacci | 0 → 1 levels with colour bands | retracement on the most recent swing leg |
| Trade setup | "Entry" / "Stop-Loss" / "Target" | Entry line + risk (red) & reward (teal) zones with labels |

### Built for readability

To keep the chart clean (the earlier version covered the candles):

- The trade setup is **projected to the right of the last candle** — like the
  TradingView position tool — so it never paints over price history.
- **Auto** mode anchors the setup on the S/R level the price is **closest to**
  (a sell at the nearest resistance above, or a buy at the nearest support
  below) — a meaningful pending order, not a stale level price already left.
  Switch **Show setup** to *Both sides* for both, or *Off* to hide it.
- Zones are highly transparent, lines are thin, and every level is labelled
  with its price.
- **Fibonacci is off by default** (it was the noisiest element); order blocks
  are faint and body-sized.

Same mirrored logic as before: a swing **high** drives the **Sell** setup
(Resistance → Stop-Loss above → Target below); a swing **low** drives the
**Buy** setup (Support → Stop-Loss below → Target above).

## How to use

1. Open TradingView → **Pine Editor**.
2. Paste the contents of `smart_trade_setup.pine`.
3. Click **Add to chart**.

## Settings

- **Swing strength** – how many bars left/right define a pivot (larger = only
  bigger swings).
- **Order blocks** – toggle, how many to keep, transparency.
- **Support / Resistance** – toggle the thin S/R lines.
- **Fibonacci** – toggle (off by default).
- **Trade setup** – **Show setup** (*Auto (nearest level)* / *Both sides* / *Off*),
  **Reward : Risk** ratio, **Stop buffer (ATR ×)** for the stop distance,
  **Setup width** (how far the zones project to the right) and **Zone
  transparency**.

> Tip: if the zones still feel large, that just reflects the real ATR-based
> risk on a volatile symbol — raise **Zone transparency** or lower **Setup
> width** to make it lighter.

## Alerts

Two alert conditions are included:

- *Sell setup* — fires when a new swing high forms.
- *Buy setup* — fires when a new swing low forms.

## Notes

- The stop distance is derived from ATR(14) × *Stop buffer*; the target is
  placed at *Reward : Risk* × the risk distance, so the green zone is always the
  configured multiple of the red zone.
- This is a charting / educational tool, not financial advice.
