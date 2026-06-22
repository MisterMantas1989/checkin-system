#!/usr/bin/env python3
"""
sr_scanner.py
=============
Scans your Bybit USDT-perp symbols and pushes a Telegram alert listing which coins
are currently NEAR a support or resistance zone — using the SAME zone logic as your
Pine indicator (pivot lookback -> ATR-merge into zones -> nearPct cull -> keep top-N
by touch count). It is a *filter to save manual scanning*, not a trade signal.

Run one pass (cron-friendly) or as an aligned 15m loop:

    export TG_BOT_TOKEN="123456:ABC..."     # from @BotFather
    export TG_CHAT_ID="987654321"           # your chat id
    python sr_scanner.py            # single scan, exits
    python sr_scanner.py --loop     # scans at every 15m candle close
    python sr_scanner.py --window   # opens the 15m loop in a new console window
    python sr_scanner.py --dry-run  # scan + print to console, no Telegram

Fidelity note: this REPLICATES the Pine logic, it does not mirror TradingView bar-for-bar
(ATR seeding / pivot-confirmation timing differ slightly). It is built to flag "look at
these" — you still open the chart and apply your own read. Strength-decay / break tracking
is intentionally omitted (irrelevant to "is price near a level"); zones are ranked by touch
count, which is exactly the Pine keep-priority. The Pine f_register near-guard (only register
a pivot that was near price at its CONFIRMATION bar) is now replicated — see near_at_confirm().
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from typing import Optional

import aiohttp

# Load env from a .env file. Priority: $SR_ENV_FILE (e.g. your old bot's .env) > local .env.
try:
    from dotenv import load_dotenv
    load_dotenv()                                   # local .env (cwd / parents), if any
    _ef = os.environ.get("SR_ENV_FILE")
    if _ef:
        load_dotenv(_ef, override=True)             # explicit path to your old .env
except ImportError:
    pass

log = logging.getLogger("sr_scanner")


def _env(*names: str) -> str:
    """First non-empty value among the given env var names (handles different .env naming)."""
    for n in names:
        v = os.environ.get(n)
        if v:
            return v
    return ""


# ───────────────────────────── Config ──────────────────────────────────────
@dataclass(frozen=True)
class Config:
    # --- 30 symbols — mirrors your TradingView watchlist (Bybit linear perp format) ---
    symbols: tuple[str, ...] = (
        "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "BNBUSDT", "DOGEUSDT",
        "ADAUSDT", "SUIUSDT", "TRXUSDT", "LTCUSDT", "AAVEUSDT", "LINKUSDT",
        "AVAXUSDT", "UNIUSDT", "APTUSDT", "INJUSDT", "ARBUSDT", "OPUSDT",
        "SEIUSDT", "TIAUSDT", "TAOUSDT", "JUPUSDT", "WIFUSDT", "ONDOUSDT",
        "ENAUSDT", "RENDERUSDT", "IMXUSDT", "FARTCOINUSDT", "HYPEUSDT", "1000PEPEUSDT",
    )
    interval: str = "15"          # 15m
    category: str = "linear"      # USDT perps
    klines: int = 250             # candles pulled per symbol (enough for pivots + ATR)

    # --- zone params: MATCHED to your Pine inputs ---
    piv_len: int = 10             # pivLen
    atr_len: int = 14             # ta.atr(14)
    merge_atr: float = 0.5        # mergeATR
    near_pct: float = 15.0        # nearPct  (cull zones beyond this % of price)
    max_zones: int = 5            # maxZones (keep N strongest by touch)

    # --- scanner-only: how close counts as "near" for an alert ---
    alert_dist_atr: float = 0.6   # alert when price within this many ATR of a zone
    min_touch: int = 1            # ignore zones with fewer touches than this (Pine has none -> keep 1)

    # --- bybit / networking ---
    base_url: str = "https://api.bybit.com"
    concurrency: int = 10
    timeout: float = 10.0
    retries: int = 3
    backoff: float = 0.8

    # --- telegram (from env / .env — tries common variable names) ---
    tg_token: str = field(default_factory=lambda: _env(
        "TG_BOT_TOKEN", "TELEGRAM_BOT_TOKEN", "BOT_TOKEN", "TELEGRAM_TOKEN"))
    tg_chat: str = field(default_factory=lambda: _env(
        "TG_CHAT_ID", "TELEGRAM_CHAT_ID", "CHAT_ID"))


# A single OHLC candle: (start_ms, open, high, low, close)
Candle = tuple[int, float, float, float, float]


# ──────────────────────── Pure analytics (ported Pine) ──────────────────────
def wilder_atr(highs: list[float], lows: list[float], closes: list[float], length: int) -> float:
    """Wilder RMA ATR — matches Pine ta.atr(length). Returns the latest ATR value."""
    n = len(closes)
    if n < length + 1:
        return 0.0
    trs = [highs[0] - lows[0]]
    for i in range(1, n):
        trs.append(max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        ))
    atr = sum(trs[1:length + 1]) / length          # seed = SMA of first `length` true TRs
    for i in range(length + 1, n):
        atr = (atr * (length - 1) + trs[i]) / length
    return atr


def find_pivots(values: list[float], left: int, right: int, is_high: bool) -> list[tuple[int, float]]:
    """Confirmed pivot highs/lows (strict on both sides), like ta.pivothigh/low(left, right)."""
    out: list[tuple[int, float]] = []
    n = len(values)
    for i in range(left, n - right):
        v = values[i]
        if is_high:
            if all(v > values[i - j] for j in range(1, left + 1)) and \
               all(v > values[i + j] for j in range(1, right + 1)):
                out.append((i, v))
        else:
            if all(v < values[i - j] for j in range(1, left + 1)) and \
               all(v < values[i + j] for j in range(1, right + 1)):
                out.append((i, v))
    return out


def near_at_confirm(piv_idx: int, piv_price: float, closes: list[float],
                    right: int, near_pct: float) -> bool:
    """Pine f_register near-guard: was the pivot within nearPct of price at its
    CONFIRMATION bar (piv_idx + right)? Replicates the Pine 'only register zones
    near price' rule so touch counts line up with the indicator."""
    j = piv_idx + right
    if j >= len(closes):
        return False                                # not yet confirmed inside the window
    c = closes[j]
    return abs(piv_price - c) <= c * near_pct / 100.0


def build_zones(pivots: list[tuple[int, float]], atr: float, merge_atr: float) -> list[dict]:
    """Merge pivots within (atr * merge_atr) into zones; running-average price + touch count.
    Mirrors the Pine f_register merge-or-push logic."""
    zones: list[dict] = []
    band = atr * merge_atr
    for _, price in pivots:                         # chronological
        best_i, best_d = -1, band
        for zi, z in enumerate(zones):
            d = abs(z["price"] - price)
            if d <= best_d:
                best_d, best_i = d, zi
        if best_i >= 0:
            z = zones[best_i]
            z["touch"] += 1
            z["price"] = (z["price"] * (z["touch"] - 1) + price) / z["touch"]
        else:
            zones.append({"price": price, "touch": 1})
    return zones


def analyze(candles: list[Candle], cfg: Config) -> Optional[dict]:
    """Build current zones for one symbol and return any that price is near."""
    if len(candles) < cfg.piv_len * 2 + cfg.atr_len + 5:
        return None
    highs = [c[2] for c in candles]
    lows = [c[3] for c in candles]
    closes = [c[4] for c in candles]
    close = closes[-1]
    atr = wilder_atr(highs, lows, closes, cfg.atr_len)
    if atr <= 0:
        return None

    pivots = find_pivots(highs, cfg.piv_len, cfg.piv_len, True) + \
        find_pivots(lows, cfg.piv_len, cfg.piv_len, False)
    pivots.sort(key=lambda p: p[0])                 # chronological for faithful merging

    # Pine fidelity: only register a pivot that was near price at its confirmation bar
    # (mirrors the f_register near-guard so touch counts match the indicator).
    pivots = [(i, p) for (i, p) in pivots
              if near_at_confirm(i, p, closes, cfg.piv_len, cfg.near_pct)]

    zones = build_zones(pivots, atr, cfg.merge_atr)

    # cull zones beyond nearPct of price (matches Pine), then keep top-N by touch
    near_abs = close * cfg.near_pct / 100.0
    zones = [z for z in zones if abs(z["price"] - close) <= near_abs and z["touch"] >= cfg.min_touch]
    zones.sort(key=lambda z: z["touch"], reverse=True)
    zones = zones[: cfg.max_zones]

    # proximity: which zones is price currently near?
    thresh = atr * cfg.alert_dist_atr
    hits = []
    for z in zones:
        dist = z["price"] - close
        if abs(dist) <= thresh:
            hits.append({
                "side": "support" if dist < 0 else "resistance",
                "price": z["price"],
                "dist_pct": dist / close * 100.0,
                "dist_atr": dist / atr,
                "touch": z["touch"],
            })
    if not hits:
        return None
    hits.sort(key=lambda h: abs(h["dist_atr"]))
    return {"close": close, "atr": atr, "hits": hits}


# ─────────────────────────── Networking (async) ─────────────────────────────
async def fetch_klines(session: aiohttp.ClientSession, cfg: Config, symbol: str,
                       sem: asyncio.Semaphore) -> tuple[str, Optional[list[Candle]]]:
    url = f"{cfg.base_url}/v5/market/kline"
    params = {"category": cfg.category, "symbol": symbol,
              "interval": cfg.interval, "limit": str(cfg.klines)}
    async with sem:
        for attempt in range(1, cfg.retries + 1):
            try:
                async with session.get(url, params=params) as r:
                    data = await r.json()
                    if data.get("retCode") != 0:
                        raise RuntimeError(data.get("retMsg", "bad retCode"))
                    rows = data["result"]["list"]            # newest-first
                    rows = rows[::-1]                        # -> oldest-first
                    candles: list[Candle] = [
                        (int(x[0]), float(x[1]), float(x[2]), float(x[3]), float(x[4]))
                        for x in rows
                    ]
                    return symbol, candles
            except Exception as e:                            # noqa: BLE001 — isolate per symbol
                if attempt == cfg.retries:
                    log.warning("fetch failed %s: %s", symbol, e)
                    return symbol, None
                await asyncio.sleep(cfg.backoff * attempt)
    return symbol, None


async def send_telegram(session: aiohttp.ClientSession, cfg: Config, text: str) -> None:
    if not cfg.tg_token or not cfg.tg_chat:
        log.error("TG_BOT_TOKEN / TG_CHAT_ID not set — printing instead:\n%s", text)
        return
    url = f"https://api.telegram.org/bot{cfg.tg_token}/sendMessage"
    payload = {"chat_id": cfg.tg_chat, "text": text,
               "parse_mode": "HTML", "disable_web_page_preview": True}
    try:
        async with session.post(url, json=payload) as r:
            if r.status != 200:
                log.error("telegram %s: %s", r.status, await r.text())
    except Exception as e:                                    # noqa: BLE001
        log.error("telegram send failed: %s", e)


# ─────────────────────────────── Formatting ─────────────────────────────────
def format_report(found: dict[str, dict]) -> str:
    sup, res = [], []
    for sym, info in found.items():
        for h in info["hits"]:
            line = (f"<b>{sym}</b>  {h['price']:.6g}  "
                    f"({h['dist_pct']:+.2f}% / {h['dist_atr']:+.2f} ATR, {h['touch']}t)")
            (sup if h["side"] == "support" else res).append((abs(h["dist_atr"]), line))
    sup.sort(); res.sort()
    out = ["📡 <b>S/R scan</b> — " + time.strftime("%Y-%m-%d %H:%M")]
    if res:
        out.append("\n🔴 <b>Near resistance</b>")
        out += [l for _, l in res]
    if sup:
        out.append("\n🟢 <b>Near support</b>")
        out += [l for _, l in sup]
    return "\n".join(out)


# ──────────────────────────────── Orchestration ─────────────────────────────
def print_scan(cfg: Config, near: dict[str, dict], clear: list[str], failed: list[str]) -> None:
    """Live console view of one scan cycle — so you can watch it work in its own window."""
    print("=" * 64)
    print(f"  scan {time.strftime('%H:%M:%S')}    |    {len(cfg.symbols)} symbols")
    print("-" * 64)
    rows = []
    for sym, info in near.items():
        h = info["hits"][0]                                   # closest level
        tag = "[R]" if h["side"] == "resistance" else "[S]"
        rows.append((abs(h["dist_atr"]),
                     f"  {tag} {sym:<14}{h['dist_atr']:+.2f} ATR  {h['dist_pct']:+6.2f}%  {h['touch']}t  @ {h['price']:.6g}"))
    rows.sort()
    for _, line in rows:
        print(line)
    if not rows:
        print("  (no coins near a level right now)")
    print("-" * 64)
    print(f"  near: {len(near)}    clear: {len(clear)}    failed: {len(failed)}")
    if clear:
        print("  clear : " + " ".join(clear))
    if failed:
        print("  failed: " + " ".join(failed))


async def scan_once(cfg: Config, dry_run: bool = False) -> None:
    timeout = aiohttp.ClientTimeout(total=cfg.timeout)
    sem = asyncio.Semaphore(cfg.concurrency)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        results = await asyncio.gather(
            *(fetch_klines(session, cfg, s, sem) for s in cfg.symbols)
        )
        near: dict[str, dict] = {}
        clear: list[str] = []
        failed: list[str] = []
        for symbol, candles in results:
            if not candles:
                failed.append(symbol)
                continue
            try:
                res = analyze(candles, cfg)
            except Exception as e:                            # noqa: BLE001
                log.warning("analyze failed %s: %s", symbol, e)
                failed.append(symbol)
                continue
            if res:
                near[symbol] = res
            else:
                clear.append(symbol)

        print_scan(cfg, near, clear, failed)                  # always: live window view
        if near and not dry_run:
            await send_telegram(session, cfg, format_report(near))
            print(f"  -> Telegram sent ({len(near)} symbol(s))")
        print("=" * 64)


async def run_loop(cfg: Config, dry_run: bool = False) -> None:
    """Scan immediately, then align to each 15m candle close (a few seconds after)."""
    await scan_once(cfg, dry_run)                            # first scan right away
    while True:
        now = time.time()
        period = 15 * 60
        sleep_for = period - (now % period) + 5             # 5s after close
        nxt = time.strftime("%H:%M:%S", time.localtime(now + sleep_for))
        print(f"  next scan at {nxt}  (in {int(sleep_for)}s)  -  Ctrl+C to stop\n")
        await asyncio.sleep(sleep_for)
        try:
            await scan_once(cfg, dry_run)
        except Exception as e:                              # noqa: BLE001
            log.error("scan pass failed: %s", e)


def main() -> None:
    ap = argparse.ArgumentParser(description="Bybit S/R proximity scanner -> Telegram")
    ap.add_argument("--loop", action="store_true", help="run continuously at each 15m close")
    ap.add_argument("--window", action="store_true",
                    help="open the 15m loop in a new console window, then exit")
    ap.add_argument("--dry-run", action="store_true", help="print to console, no Telegram")
    ap.add_argument("--env", metavar="PATH", help="path to a .env file (e.g. your old bot's .env)")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    if args.window:
        # Self-spawn the 15m loop in a brand-new console window (Windows).
        # Robust: pure subprocess, no .bat. The new window inherits this env
        # and runs from the script's own folder so .env is found.
        here = os.path.dirname(os.path.abspath(__file__)) or "."
        child = [sys.executable, os.path.abspath(__file__), "--loop"]
        if args.dry_run:
            child.append("--dry-run")
        if args.env:
            child += ["--env", args.env]
        if args.verbose:
            child.append("-v")
        flags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
        subprocess.Popen(child, cwd=here, creationflags=flags, close_fds=True)
        print("Scanner startad i ett nytt fonster - 15m-loopen kor dar.")
        return

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    if args.env:
        try:
            from dotenv import load_dotenv
            load_dotenv(args.env, override=True)
        except ImportError:
            log.warning("python-dotenv not installed; --env ignored")
    cfg = Config()

    if not cfg.tg_token or not cfg.tg_chat:
        ef = os.environ.get("SR_ENV_FILE", "") or (args.env or "")
        log.warning("Telegram creds not found in env.")
        log.warning("  SR_ENV_FILE/--env = %r  (exists: %s)", ef,
                    os.path.isfile(ef) if ef else False)
        log.warning("  cwd = %s  (looked for a .env here too)", os.getcwd())
        log.warning("  Fix: put sr_scanner.py + .env in the same folder, "
                    "or point --env / SR_ENV_FILE at the .env's full path.")

    if args.loop:
        asyncio.run(run_loop(cfg, args.dry_run))
    else:
        asyncio.run(scan_once(cfg, args.dry_run))


if __name__ == "__main__":
    main()
