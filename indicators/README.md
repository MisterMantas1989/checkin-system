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
| Trade setup | "Entry Short" / "Stop-Loss" / "Target" | Entry line + risk (red) & reward (teal) zones with labels |

When a swing **high** confirms, a **short** setup is drawn (Resistance →
Entry Short, Stop-Loss zone above, Target zone below). When a swing **low**
confirms, the mirrored **long** setup is drawn (Support → Entry Long, Stop-Loss
below, Target above).

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

- *New resistance / short setup* — fires when a new swing high forms.
- *New support / long setup* — fires when a new swing low forms.

## Notes

- The stop distance is derived from ATR(14) × *Stop buffer*; the target is
  placed at *Reward : Risk* × the risk distance, so the green zone is always the
  configured multiple of the red zone.
- This is a charting / educational tool, not financial advice.
