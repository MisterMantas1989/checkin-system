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

Both the **buy** and **sell** sides are shown at the same time, using the same
mirrored logic:

- A confirmed swing **high** refreshes the **Sell** setup — Resistance →
  Sell Entry, Stop-Loss zone above, Target zone below.
- A confirmed swing **low** refreshes the **Buy** setup — Support → Buy Entry,
  Stop-Loss zone below, Target zone above.

Each side is maintained independently, so the latest buy setup and the latest
sell setup stay on the chart together.

## How to use

1. Open TradingView → **Pine Editor**.
2. Paste the contents of `smart_trade_setup.pine`.
3. Click **Add to chart**.

## Settings

- **Swing strength** – how many bars left/right define a pivot (larger = only
  bigger swings).
- **Order blocks** – toggle, max count, width and colours.
- **Fibonacci** – toggle and right-extension of the levels.
- **Trade setup** – toggle, **Reward : Risk** ratio, **Stop buffer (ATR ×)** for
  the stop distance, box width and the risk/reward zone colours.

## Alerts

Two alert conditions are included:

- *Sell setup* — fires when a new swing high forms.
- *Buy setup* — fires when a new swing low forms.

## Notes

- The stop distance is derived from ATR(14) × *Stop buffer*; the target is
  placed at *Reward : Risk* × the risk distance, so the green zone is always the
  configured multiple of the red zone.
- This is a charting / educational tool, not financial advice.
