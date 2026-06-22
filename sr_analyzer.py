#!/usr/bin/env python3
"""
sr_analyzer.py — local decision-support dashboard for the S/R scanner.

Runs the SAME 15m scan as sr_scanner.py (reuses its logic). When a coin is
flagged near a level, it pulls the *objective, decision-relevant* context you'd
otherwise gather by hand and lays it out in a dark web UI on 127.0.0.1:8000:

    • the flagged level (side, distance in ATR + %, touches)
    • HTF structure (1h / 4h: up / down / range) — objective, not a forecast
    • funding rate + next funding   (the one feature that survived residualization)
    • open interest + change        (crowding)
    • 24h volume / turnover         (is the symbol liquid enough)
    • Stoch RSI at the level        (one OB/OS readout, not a verdict)
    • nearest liquidity pools (equal highs/lows above & below)
    • RISK GEOMETRY for a fixed-% trade off the level: entry / stop / target,
      qty, notional, leverage needed, R:R  — direction-agnostic sizing math.

It does NOT output "enter / risky". That verdict is the falsified directional
hypothesis wearing a UI. This panel gives you the numbers; the call is yours.

Run:
    pip install fastapi uvicorn aiohttp python-dotenv
    python sr_analyzer.py            # opens http://127.0.0.1:8000
Keep .env (Telegram creds, optional here) in the same folder, like the scanner.
"""
from __future__ import annotations

import argparse
import asyncio
import contextlib
import logging
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from typing import Optional

# Use the OS trust store for TLS (fixes Windows cert-verification failures to
# api.telegram.org). Must run before any network lib builds its SSL context.
try:
    import truststore
    truststore.inject_into_ssl()
except Exception:  # truststore not installed -> fall back to default (certifi)
    pass

import aiohttp
import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

# Reuse the scanner's vetted logic — single source of truth for the S/R math.
from sr_scanner import (
    Candle,
    Config,
    analyze,
    build_zones,
    fetch_klines,
    find_pivots,
    format_report,
    near_at_confirm,
    send_telegram,
    wilder_atr,
)

import sr_journal as journal

log = logging.getLogger("sr_analyzer")

# ───────────────────────────── analyzer config ─────────────────────────────
HOST = "127.0.0.1"
PORT = 8000
HTF_PIV = 5          # pivot half-width for HTF structure read
STOP_ATR = 0.5       # stop placed this many ATR beyond the level
EQ_TOL = 0.15        # equal-high/low tolerance (× ATR) for liquidity pools
SEND_TELEGRAM = True # also push the scanner's Telegram summary each cycle


@dataclass
class Settings:
    """User-editable risk inputs (live, from the UI)."""
    account: float = 120.0
    risk_pct: float = 1.0


# ────────────────────────── extra analytics (pure) ──────────────────────────
def _rsi_series(closes: list[float], length: int = 14) -> list[Optional[float]]:
    """Wilder RSI as a padded series (None until enough data)."""
    n = len(closes)
    out: list[Optional[float]] = [None] * n
    if n < length + 1:
        return out
    gains = [0.0]
    losses = [0.0]
    for i in range(1, n):
        ch = closes[i] - closes[i - 1]
        gains.append(max(ch, 0.0))
        losses.append(max(-ch, 0.0))
    ag = sum(gains[1:length + 1]) / length
    al = sum(losses[1:length + 1]) / length

    def rsi(ag: float, al: float) -> float:
        if al == 0:
            return 100.0
        return 100.0 - 100.0 / (1.0 + ag / al)

    out[length] = rsi(ag, al)
    for i in range(length + 1, n):
        ag = (ag * (length - 1) + gains[i]) / length
        al = (al * (length - 1) + losses[i]) / length
        out[i] = rsi(ag, al)
    return out


def stoch_rsi(closes: list[float], rsi_len: int = 14, stoch_len: int = 14,
              k: int = 3, d: int = 3) -> Optional[dict]:
    """Stoch RSI (%K, %D) — one OB/OS readout at the level. Not a signal."""
    seq = [v for v in _rsi_series(closes, rsi_len) if v is not None]
    if len(seq) < stoch_len + k + d:
        return None
    stoch = []
    for i in range(stoch_len - 1, len(seq)):
        w = seq[i - stoch_len + 1:i + 1]
        lo, hi = min(w), max(w)
        stoch.append(0.0 if hi == lo else (seq[i] - lo) / (hi - lo) * 100.0)

    def sma(a: list[float], p: int) -> list[float]:
        return [sum(a[i - p + 1:i + 1]) / p for i in range(p - 1, len(a))]

    kline = sma(stoch, k)
    if len(kline) < d:
        return None
    dline = sma(kline, d)
    kv, dv = kline[-1], dline[-1]
    state = "overbought" if kv >= 80 else "oversold" if kv <= 20 else "neutral"
    return {"k": kv, "d": dv, "state": state}


def htf_trend(highs: list[float], lows: list[float]) -> str:
    """Objective structure read: HH+HL = up, LH+LL = down, else range."""
    ph = find_pivots(highs, HTF_PIV, HTF_PIV, True)
    pl = find_pivots(lows, HTF_PIV, HTF_PIV, False)
    if len(ph) < 2 or len(pl) < 2:
        return "range"
    hh = ph[-1][1] > ph[-2][1]
    hl = pl[-1][1] > pl[-2][1]
    lh = ph[-1][1] < ph[-2][1]
    ll = pl[-1][1] < pl[-2][1]
    if hh and hl:
        return "up"
    if lh and ll:
        return "down"
    return "range"


def zone_ladder(candles: list[Candle], cfg: Config) -> tuple[list[float], float, float]:
    """All current zones near price (sorted by price) + atr + close — for targets."""
    highs = [c[2] for c in candles]
    lows = [c[3] for c in candles]
    closes = [c[4] for c in candles]
    close = closes[-1]
    atr = wilder_atr(highs, lows, closes, cfg.atr_len)
    if atr <= 0:
        return [], 0.0, close
    pivots = (find_pivots(highs, cfg.piv_len, cfg.piv_len, True)
              + find_pivots(lows, cfg.piv_len, cfg.piv_len, False))
    pivots.sort(key=lambda p: p[0])
    # Pine fidelity: same near-guard as the scanner so the ladder's zones match
    pivots = [(i, p) for (i, p) in pivots
              if near_at_confirm(i, p, closes, cfg.piv_len, cfg.near_pct)]
    zones = build_zones(pivots, atr, cfg.merge_atr)
    near_abs = close * cfg.near_pct / 100.0
    prices = sorted(z["price"] for z in zones if abs(z["price"] - close) <= near_abs)
    return prices, atr, close


def liquidity_pools(candles: list[Candle], atr: float, cfg: Config) -> dict:
    """Nearest equal-high cluster above (buyside) and equal-low cluster below (sellside)."""
    if atr <= 0:
        return {"buyside": None, "sellside": None}
    highs = [c[2] for c in candles]
    lows = [c[3] for c in candles]
    close = candles[-1][4]
    tol = atr * EQ_TOL
    ph = [p for _, p in find_pivots(highs, cfg.piv_len, cfg.piv_len, True)]
    pl = [p for _, p in find_pivots(lows, cfg.piv_len, cfg.piv_len, False)]

    def cluster(levels: list[float]) -> list[float]:
        out: list[tuple[float, int]] = []
        for v in sorted(levels):
            for i, (m, c) in enumerate(out):
                if abs(m - v) <= tol:
                    out[i] = ((m * c + v) / (c + 1), c + 1)
                    break
            else:
                out.append((v, 1))
        return [m for m, c in out if c >= 2]

    buy = [m for m in cluster(ph) if m > close]
    sell = [m for m in cluster(pl) if m < close]
    return {
        "buyside": min(buy) if buy else None,    # nearest above
        "sellside": max(sell) if sell else None,  # nearest below
    }


def sizing(core: dict, s: Settings) -> Optional[dict]:
    """Risk geometry for taking the flagged level. Direction-agnostic math, no advice."""
    close, atr, level = core["close"], core["atr15"], core["level"]
    long = core["side"] == "support"          # support -> long, resistance -> short
    buf = STOP_ATR * atr
    entry = close
    if long:
        stop = level - buf
        target = next((p for p in core["ladder"] if p > entry + 1e-12), None)
    else:
        stop = level + buf
        target = next((p for p in reversed(core["ladder"]) if p < entry - 1e-12), None)
    rpu = abs(entry - stop)
    if rpu <= 0 or s.account <= 0:
        return None
    risk_amt = s.account * s.risk_pct / 100.0
    qty = risk_amt / rpu
    notional = qty * entry
    out = {
        "long": long,
        "entry": entry,
        "stop": stop,
        "stop_pct": (stop - entry) / entry * 100.0,
        "risk_per_unit": rpu,
        "risk_amount": risk_amt,
        "qty": qty,
        "notional": notional,
        "leverage": notional / s.account,
        "target": target,
        "rr": None,
        "target_pct": None,
    }
    if target is not None:
        out["rr"] = abs(target - entry) / rpu
        out["target_pct"] = (target - entry) / entry * 100.0
    return out


# ───────────────────────────── network helpers ──────────────────────────────
async def fetch_tf(session: aiohttp.ClientSession, cfg: Config, symbol: str,
                   interval: str, limit: int, sem: asyncio.Semaphore
                   ) -> Optional[list[Candle]]:
    """Generic kline fetch for an arbitrary timeframe (HTF context)."""
    url = f"{cfg.base_url}/v5/market/kline"
    params = {"category": cfg.category, "symbol": symbol,
              "interval": interval, "limit": str(limit)}
    async with sem:
        try:
            async with session.get(url, params=params) as r:
                data = await r.json()
                if data.get("retCode") != 0:
                    return None
                rows = data["result"]["list"][::-1]
                return [(int(x[0]), float(x[1]), float(x[2]), float(x[3]), float(x[4]))
                        for x in rows]
        except Exception as e:  # noqa: BLE001
            log.debug("fetch_tf %s %s: %s", symbol, interval, e)
            return None


async def fetch_ticker(session: aiohttp.ClientSession, cfg: Config, symbol: str,
                       sem: asyncio.Semaphore) -> dict:
    """Funding, OI, 24h volume/turnover, 24h % — one call."""
    url = f"{cfg.base_url}/v5/market/tickers"
    params = {"category": cfg.category, "symbol": symbol}
    async with sem:
        try:
            async with session.get(url, params=params) as r:
                data = await r.json()
                row = data["result"]["list"][0]
                return {
                    "funding": float(row.get("fundingRate", 0) or 0) * 100.0,
                    "next_funding": int(row.get("nextFundingTime", 0) or 0),
                    "oi": float(row.get("openInterest", 0) or 0),
                    "oi_value": float(row.get("openInterestValue", 0) or 0),
                    "vol24h": float(row.get("volume24h", 0) or 0),
                    "turnover24h": float(row.get("turnover24h", 0) or 0),
                    "pcnt24h": float(row.get("price24hPcnt", 0) or 0) * 100.0,
                }
        except Exception as e:  # noqa: BLE001
            log.debug("ticker %s: %s", symbol, e)
            return {}


async def fetch_oi_change(session: aiohttp.ClientSession, cfg: Config, symbol: str,
                          sem: asyncio.Semaphore) -> Optional[float]:
    """1h open-interest change %."""
    url = f"{cfg.base_url}/v5/market/open-interest"
    params = {"category": cfg.category, "symbol": symbol,
              "intervalTime": "1h", "limit": "2"}
    async with sem:
        try:
            async with session.get(url, params=params) as r:
                data = await r.json()
                lst = data["result"]["list"]            # newest-first
                cur = float(lst[0]["openInterest"])
                prev = float(lst[1]["openInterest"])
                return (cur - prev) / prev * 100.0 if prev else None
        except Exception as e:  # noqa: BLE001
            log.debug("oi_change %s: %s", symbol, e)
            return None


# ─────────────────────────── deep analysis per coin ─────────────────────────
async def deep_analysis(session: aiohttp.ClientSession, cfg: Config, symbol: str,
                        hit: dict, c15: list[Candle], sem: asyncio.Semaphore) -> dict:
    """Network-derived 'core' for a flagged coin. Sizing is computed later from settings."""
    c1h, c4h, tick, oi_chg = await asyncio.gather(
        fetch_tf(session, cfg, symbol, "60", 200, sem),
        fetch_tf(session, cfg, symbol, "240", 200, sem),
        fetch_ticker(session, cfg, symbol, sem),
        fetch_oi_change(session, cfg, symbol, sem),
    )
    ladder, atr15, close = zone_ladder(c15, cfg)
    liq = liquidity_pools(c15, atr15, cfg)
    srsi = stoch_rsi([c[4] for c in c15])

    def trend(c: Optional[list[Candle]]) -> Optional[str]:
        if not c:
            return None
        return htf_trend([x[2] for x in c], [x[3] for x in c])

    return {
        "symbol": symbol,
        "close": close,
        "atr15": atr15,
        "side": hit["side"],
        "level": hit["price"],
        "dist_atr": hit["dist_atr"],
        "dist_pct": hit["dist_pct"],
        "touch": hit["touch"],
        "ladder": ladder,
        "trend_15m": trend(c15),
        "trend_1h": trend(c1h),
        "trend_4h": trend(c4h),
        "stoch_rsi": srsi,
        "liq_buyside": liq["buyside"],
        "liq_sellside": liq["sellside"],
        "oi_change_1h": oi_chg,
        "candles": [[x[1], x[2], x[3], x[4]] for x in c15[-80:]],  # [o,h,l,c] for the UI chart
        **tick,
    }


# ────────────────────────────── scan + state ────────────────────────────────
class State:
    """Single-writer (scan loop) / many-reader (HTTP) snapshot. Swapped atomically."""
    def __init__(self) -> None:
        self.scan_time: float = 0.0
        self.next_scan: float = 0.0
        self.cores: list[dict] = []
        self.clear: int = 0
        self.failed: int = 0
        self.scanning: bool = False


STATE = State()
SETTINGS = Settings()
CFG = Config()

JOURNAL_SYNC_SEC = 300          # auto-pull closed trades every 5 min


class JSync:
    """Journal sync status surfaced to the UI."""
    def __init__(self) -> None:
        self.last_sync: float = 0.0
        self.last_result: dict = {}
        self.syncing: bool = False


JSYNC = JSync()


async def journal_sync(days: int = 7) -> dict:
    JSYNC.syncing = True
    try:
        res = await journal.do_sync(days=days)
        JSYNC.last_result = res
        if res.get("ok"):
            JSYNC.last_sync = time.time()
        return res
    finally:
        JSYNC.syncing = False


async def journal_loop() -> None:
    await asyncio.to_thread(journal.init_db)
    if journal.has_keys():
        await journal_sync(days=7)              # initial pull on startup
    while True:
        await asyncio.sleep(JOURNAL_SYNC_SEC)
        if journal.has_keys():
            try:
                await journal_sync(days=7)
            except Exception as e:              # noqa: BLE001
                log.exception("journal sync failed: %s", e)


# ─────────────── Telegram alert (rich — mirrors the UI detail panel) ─────────
_TR = {"up": "▲", "down": "▼", "range": "≈"}


def _sv(x: Optional[float], d: int = 2) -> str:
    """Swedish-formatted number (space thousands, comma decimal) — matches the UI."""
    if x is None:
        return "—"
    return f"{x:,.{d}f}".replace(",", " ").replace(".", ",")


def _px(x: Optional[float]) -> str:
    if x is None:
        return "—"
    return _sv(x, 2 if abs(x) >= 1 else 5)


def _sgn(x: Optional[float]) -> str:
    return "+" if (x is not None and x > 0) else ""


def _alert_block(core: dict, s: Settings) -> str:
    sym = core["symbol"].replace("USDT", "")
    is_sup = core["side"] == "support"
    emoji = "🟢" if is_sup else "🔴"
    sidetxt = "STÖD" if is_sup else "MOTSTÅND"

    p = core.get("pcnt24h")
    ptxt = "—" if p is None else f"{_sgn(p)}{_sv(p)}%"
    head = (f"{emoji} <b>{sym}</b> — {sidetxt}\n"
            f"<code>{_px(core['close'])}</code> · {ptxt} 24h")

    niv = (f"<b>nivå</b>  {_px(core['level'])} · {_sv(abs(core['dist_atr']))} ATR "
           f"({_sgn(core['dist_pct'])}{_sv(core['dist_pct'])}%) · {core['touch']}×")

    tr = lambda t: _TR.get(t, "—")
    struc = (f"<b>struktur</b>  15m {tr(core.get('trend_15m'))} · "
             f"1h {tr(core.get('trend_1h'))} · 4h {tr(core.get('trend_4h'))}")
    srsi = core.get("stoch_rsi")
    if srsi and srsi.get("k") is not None:
        st = ("OB" if srsi.get("state") == "overbought"
              else "OS" if srsi.get("state") == "oversold" else "")
        struc += f" · SRSI {_sv(srsi['k'], 0)}/{_sv(srsi['d'], 0)}{(' ' + st) if st else ''}"

    f = core.get("funding")
    fundtxt = "—" if f is None else f"{_sgn(f)}{_sv(f, 4)}%"
    oi = core.get("oi_change_1h")
    oitxt = "—" if oi is None else f"{_sgn(oi)}{_sv(oi)}%"
    turn = core.get("turnover24h")
    turntxt = "—" if turn is None else f"${_sv(turn / 1e6, 1)}M"
    mark = f"<b>marknad</b>  fund {fundtxt} · OI {oitxt} · vol {turntxt}"

    liq = (f"<b>likviditet</b>  ↑{_px(core.get('liq_buyside'))} · "
           f"↓{_px(core.get('liq_sellside'))}")

    sz = sizing(core, s)
    if sz is None:
        risk = "<b>risk</b>  sätt konto + risk % i panelen"
    else:
        lev = sz["leverage"]
        lemoji = "🟢" if lev <= 3 else "🟡" if lev <= 6 else "🔴"
        side = "lång" if sz["long"] else "kort"
        tp = ("—" if sz["target"] is None
              else f"{_px(sz['target'])} ({_sgn(sz['target_pct'])}{_sv(sz['target_pct'])}%)")
        rr = "—" if sz["rr"] is None else f"{_sv(sz['rr'], 1)}R"
        win = "—" if sz["rr"] is None else f"+${_sv(sz['risk_amount'] * sz['rr'])}"
        risk = (f"<b>risk ({side})</b>  entry {_px(sz['entry'])} · "
                f"SL {_px(sz['stop'])} ({_sv(sz['stop_pct'])}%) · TP {tp}\n"
                f"  −${_sv(sz['risk_amount'])} / {win} · <b>{rr}</b> · {lemoji} <b>{_sv(lev, 2)}x</b>")

    return "\n".join([head, "", niv, struc, mark, liq, risk])


def format_alert(cores: list[dict], s: Settings) -> list[str]:
    """Rich Telegram message(s) mirroring the dashboard. Split to stay < Telegram's 4096 cap."""
    if not cores:
        return []
    header = (f"📡 <b>S/R SCAN</b> · {time.strftime('%Y-%m-%d %H:%M')}\n"
              f"{len(cores)} nära nivå · sorterat på närhet")
    chunks: list[str] = []
    cur = header
    for c in cores:
        block = _alert_block(c, s)
        cand = cur + "\n\n" + block
        if len(cand) > 3800:
            chunks.append(cur)
            cur = block
        else:
            cur = cand
    chunks.append(cur)
    return chunks


async def scan_cycle(session: aiohttp.ClientSession) -> None:
    sem = asyncio.Semaphore(CFG.concurrency)
    STATE.scanning = True
    try:
        results = await asyncio.gather(
            *(fetch_klines(session, CFG, s, sem) for s in CFG.symbols)
        )
        near: dict[str, dict] = {}
        clear = failed = 0
        candles: dict[str, list[Candle]] = {}
        for sym, c in results:
            if c is None:
                failed += 1
                continue
            res = analyze(c, CFG)
            if res:
                near[sym] = res["hits"][0]          # closest level
                candles[sym] = c
            else:
                clear += 1

        cores = await asyncio.gather(
            *(deep_analysis(session, CFG, s, near[s], candles[s], sem) for s in near)
        ) if near else []
        cores.sort(key=lambda d: abs(d["dist_atr"]))

        STATE.cores = list(cores)
        STATE.clear = clear
        STATE.failed = failed
        STATE.scan_time = time.time()

        if SEND_TELEGRAM and cores:
            for msg in format_alert(cores, SETTINGS):
                await send_telegram(session, CFG, msg)
    finally:
        STATE.scanning = False


async def scan_loop() -> None:
    timeout = aiohttp.ClientTimeout(total=CFG.timeout)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        await scan_cycle(session)                    # immediate first scan
        period = 15 * 60
        while True:
            now = time.time()
            STATE.next_scan = (now // period + 1) * period + 5
            await asyncio.sleep(max(1.0, STATE.next_scan - now))
            try:
                await scan_cycle(session)
            except Exception as e:  # noqa: BLE001 — keep the loop alive
                log.exception("scan cycle failed: %s", e)


# ─────────────────────────────── FastAPI app ────────────────────────────────
@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    tasks = [asyncio.create_task(scan_loop()),
             asyncio.create_task(journal_loop())]
    try:
        yield
    finally:
        for t in tasks:
            t.cancel()
        for t in tasks:
            with contextlib.suppress(asyncio.CancelledError):
                await t


app = FastAPI(title="S/R Analyzer", lifespan=lifespan)


class SettingsIn(BaseModel):
    account: float
    risk_pct: float


@app.get("/", response_class=HTMLResponse)
async def index() -> str:
    return PAGE


@app.post("/api/settings")
async def set_settings(s: SettingsIn) -> JSONResponse:
    SETTINGS.account = max(0.0, s.account)
    SETTINGS.risk_pct = max(0.0, s.risk_pct)
    return JSONResponse({"ok": True})


@app.get("/api/state")
async def get_state() -> JSONResponse:
    coins = []
    for core in STATE.cores:
        item = dict(core)
        item["sizing"] = sizing(core, SETTINGS)
        coins.append(item)
    return JSONResponse({
        "scan_time": STATE.scan_time,
        "next_scan": STATE.next_scan,
        "scanning": STATE.scanning,
        "clear": STATE.clear,
        "failed": STATE.failed,
        "symbols": len(CFG.symbols),
        "account": SETTINGS.account,
        "risk_pct": SETTINGS.risk_pct,
        "coins": coins,
    })


class TagIn(BaseModel):
    order_id: str
    setup_type: Optional[str] = None
    with_trend: Optional[str] = None
    from_scanner: Optional[int] = None
    planned_risk: Optional[float] = None
    mistakes: Optional[str] = None
    rating: Optional[int] = None
    note: Optional[str] = None


@app.get("/api/journal/state")
async def journal_state() -> JSONResponse:
    trades = await asyncio.to_thread(journal.list_trades, 300)
    stats = await asyncio.to_thread(journal.analytics)
    return JSONResponse({
        "trades": trades,
        "stats": stats,
        "has_keys": journal.has_keys(),
        "syncing": JSYNC.syncing,
        "last_sync": JSYNC.last_sync,
        "last_result": JSYNC.last_result,
    })


@app.post("/api/journal/tag")
async def journal_tag(t: TagIn) -> JSONResponse:
    tags = {k: v for k, v in t.model_dump().items()
            if k != "order_id" and v is not None}
    ok = await asyncio.to_thread(journal.update_tags, t.order_id, tags)
    return JSONResponse({"ok": ok})


@app.post("/api/journal/sync")
async def journal_sync_now() -> JSONResponse:
    if not journal.has_keys():
        return JSONResponse({"ok": False, "error": "no_keys"})
    res = await journal_sync(days=30)           # manual sync reaches back further
    return JSONResponse(res)


# ─────────────────────────────── dark UI ────────────────────────────────────
PAGE = r"""<!doctype html>
<html lang="sv"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>S/R Analyzer</title>
<style>
  :root{
    /* palette — graphite trading desk */
    --bg:#0a0d12; --panel:#0f141c; --panel-2:#141a24; --inset:#0b0f15;
    --line:#1e2632; --line-2:#2b3543;
    --txt:#e9eef5; --dim:#8a96a8; --faint:#5a6576;
    --accent:#41d6c3; --accent-dim:#1c8e84;
    --long:#34c27a; --short:#f26d86; --amber:#e2a93b;
    --sup:#56b6e6; --res:#f26d86; --chip:#141a24; --sel:#121a26;
    --r:8px; --r-sm:6px;
    --font-ui:system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;
    --font-mono:ui-monospace,"Cascadia Mono","SF Mono","JetBrains Mono",Menlo,Consolas,monospace;
  }
  *{box-sizing:border-box}
  html,body{height:100%}
  body{margin:0;background:var(--bg);color:var(--txt);display:flex;flex-direction:column;
    font:13px/1.55 var(--font-mono);font-variant-numeric:tabular-nums;
    -webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility}
  ::selection{background:rgba(65,214,195,.25)}
  *::-webkit-scrollbar{width:10px;height:10px}
  *::-webkit-scrollbar-thumb{background:var(--line-2);border-radius:6px;border:2px solid var(--bg)}
  *::-webkit-scrollbar-thumb:hover{background:#3a4759}
  *::-webkit-scrollbar-track{background:transparent}

  /* ── header ── */
  header{position:sticky;top:0;z-index:20;
    background:linear-gradient(180deg,rgba(15,20,28,.96),rgba(11,14,19,.92));
    backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px);
    border-bottom:1px solid var(--line);padding:11px 20px;
    display:flex;align-items:center;gap:20px;flex-wrap:wrap;flex-shrink:0}
  header::after{content:"";position:absolute;left:0;right:0;bottom:-1px;height:1px;
    background:linear-gradient(90deg,transparent,rgba(65,214,195,.45),transparent)}
  h1{font-family:var(--font-ui);font-size:13px;margin:0;font-weight:600;
    letter-spacing:.14em;color:var(--dim);display:flex;align-items:center;gap:8px}
  h1 span{color:var(--txt);font-weight:700}
  h1::before{content:"";width:7px;height:7px;border-radius:2px;background:var(--accent);
    box-shadow:0 0 10px rgba(65,214,195,.7)}

  .meta{font-family:var(--font-ui);color:var(--faint);font-size:11.5px;
    display:flex;gap:18px;flex-wrap:wrap;align-items:center}
  .meta b{color:var(--txt);font-weight:600;font-family:var(--font-mono)}
  .settings{margin-left:auto;display:flex;gap:14px;align-items:center}
  .settings label{font-family:var(--font-ui);color:var(--faint);font-size:11.5px;
    display:flex;align-items:center;gap:7px}
  .settings input{width:74px;background:var(--inset);border:1px solid var(--line);
    color:var(--txt);border-radius:var(--r-sm);padding:6px 9px;
    font:600 13px var(--font-mono);text-align:right;transition:border-color .15s,box-shadow .15s}
  .settings input:focus{outline:none;border-color:var(--accent-dim);
    box-shadow:0 0 0 3px rgba(65,214,195,.12)}

  .note{font-family:var(--font-ui);color:var(--faint);font-size:11px;line-height:1.5;
    padding:8px 20px;border-bottom:1px solid var(--line);flex-shrink:0;background:var(--panel)}

  .pulse{width:8px;height:8px;border-radius:50%;background:var(--faint);
    display:inline-block;vertical-align:middle;transition:background .2s}
  .pulse.on{background:var(--accent);animation:pulse 1.6s ease-out infinite}
  @keyframes pulse{0%{box-shadow:0 0 0 0 rgba(65,214,195,.5)}
    70%{box-shadow:0 0 0 7px rgba(65,214,195,0)}100%{box-shadow:0 0 0 0 rgba(65,214,195,0)}}

  /* ── tabs (segmented) ── */
  .tabs{display:flex;gap:3px;background:var(--inset);border:1px solid var(--line);
    border-radius:var(--r);padding:3px}
  .tab{font-family:var(--font-ui);background:transparent;border:0;color:var(--dim);
    padding:6px 16px;border-radius:6px;font-size:12px;font-weight:500;cursor:pointer;
    transition:color .15s,background .15s}
  .tab:hover{color:var(--txt)}
  .tab.on{background:var(--panel-2);color:var(--txt);
    box-shadow:inset 0 0 0 1px var(--line-2),0 1px 2px rgba(0,0,0,.3)}

  /* ── layout ── */
  .layout{flex:1;display:flex;min-height:0}
  .scanner-view,.journal-view{flex:1;min-height:0}
  .scanner-view{display:none}
  .journal-view{display:none;overflow:auto;padding:22px 26px}
  body.tab-scanner .scanner-view{display:flex}
  body.tab-journal .journal-view{display:block}
  body.tab-journal .scanner-only{display:none}

  /* ── list (triage rail) ── */
  aside{width:290px;flex-shrink:0;border-right:1px solid var(--line);
    overflow:auto;background:var(--panel)}
  .li{position:relative;display:grid;grid-template-columns:1fr auto;gap:4px 10px;
    align-items:center;padding:12px 16px 12px 17px;border-bottom:1px solid var(--line);
    cursor:pointer;transition:background .12s}
  .li:hover{background:var(--panel-2)}
  .li.sel{background:var(--sel)}
  .li.sel::before{content:"";position:absolute;left:0;top:0;bottom:0;width:3px;
    background:var(--accent);box-shadow:0 0 12px rgba(65,214,195,.5)}
  .li .top{display:flex;align-items:center;gap:10px}
  .dot{width:8px;height:8px;border-radius:50%;flex-shrink:0}
  .dot.support{background:var(--sup);box-shadow:0 0 0 3px rgba(86,182,230,.16)}
  .dot.resistance{background:var(--res);box-shadow:0 0 0 3px rgba(242,109,134,.16)}
  .lsym{font-weight:700;font-size:14px;letter-spacing:.02em}
  .lside{font-family:var(--font-ui);font-size:9.5px;font-weight:600;color:var(--faint);
    letter-spacing:.09em;justify-self:end}
  .lmeta{grid-column:1/-1;display:flex;gap:14px;color:var(--dim);font-size:11px;padding-left:18px}
  .lmeta .lev{font-weight:700}

  /* ── detail ── */
  main{flex:1;overflow:auto;padding:26px 32px}
  .empty{font-family:var(--font-ui);color:var(--faint);text-align:center;
    padding:90px 20px;font-size:13px}
  .dhead{display:flex;align-items:baseline;gap:16px;margin-bottom:4px;
    padding-bottom:18px;border-bottom:1px solid var(--line);max-width:600px}
  .dsym{font-size:28px;font-weight:800;letter-spacing:.01em;line-height:1}
  .dpx{color:var(--dim);font-size:13px}
  .tag{font-family:var(--font-ui);font-size:10px;font-weight:700;letter-spacing:.08em;
    padding:5px 12px;border-radius:6px;margin-left:auto;align-self:center}
  .tag.support{color:#06222f;background:var(--sup)}
  .tag.resistance{color:#2c0a13;background:var(--res)}

  .sect{margin-top:22px;max-width:600px}
  .sect h3{font-family:var(--font-ui);margin:0 0 9px;font-size:10px;color:var(--faint);
    text-transform:uppercase;letter-spacing:.12em;font-weight:600;
    display:flex;align-items:center;gap:8px}
  .sect h3::before{content:"";width:3px;height:11px;border-radius:2px;background:var(--line-2)}
  .drow{display:flex;justify-content:space-between;gap:16px;padding:8px 0;
    border-bottom:1px solid var(--line)}
  .drow:last-child{border-bottom:0}
  .drow .k{font-family:var(--font-ui);color:var(--dim);font-size:12px}
  .drow .v{text-align:right;font-weight:500}
  .v.big{font-size:15px;font-weight:600}
  .chips{display:flex;gap:8px;flex-wrap:wrap}
  .chip{font-family:var(--font-ui);font-size:11px;padding:6px 12px;border-radius:7px;
    background:var(--chip);border:1px solid var(--line);color:var(--faint);
    display:inline-flex;gap:7px;align-items:center;letter-spacing:.02em}
  .chip b{color:var(--txt);font-family:var(--font-mono);font-weight:600}

  /* semantic */
  .up{color:var(--long)} .down{color:var(--short)} .rng{color:var(--amber)}
  .lev-g{color:var(--long)} .lev-a{color:var(--amber)} .lev-r{color:var(--short)}
  .dim{color:var(--dim)}

  /* ── journal ── */
  .jbar{display:flex;align-items:center;gap:20px;flex-wrap:wrap;margin-bottom:20px}
  .jstats{display:flex;gap:14px;flex-wrap:wrap}
  .stat{display:flex;flex-direction:column;gap:5px;background:var(--panel);
    border:1px solid var(--line);border-radius:var(--r);padding:11px 16px;min-width:98px}
  .stat .lbl{font-family:var(--font-ui);color:var(--faint);font-size:9.5px;
    text-transform:uppercase;letter-spacing:.1em;font-weight:600}
  .stat .num{font-size:21px;font-weight:700;line-height:1}
  .jsync{margin-left:auto;display:flex;align-items:center;gap:14px}
  .warn{color:var(--amber);font-size:11px;font-family:var(--font-ui)}
  .banner{font-family:var(--font-ui);background:rgba(226,169,59,.07);
    border:1px solid rgba(226,169,59,.4);border-radius:var(--r);
    padding:13px 16px;margin-bottom:18px;font-size:12.5px;line-height:1.5;color:var(--txt)}
  .banner b{color:var(--amber)}

  .jsetups{margin-bottom:24px;overflow:auto}
  .jsetups h3{font-family:var(--font-ui);color:var(--faint);font-size:10px;
    text-transform:uppercase;letter-spacing:.12em;margin:0 0 10px;font-weight:600}
  table{border-collapse:collapse;width:100%;font-size:12px}
  thead th{position:sticky;top:0;background:var(--panel);z-index:1}
  th{font-family:var(--font-ui);text-align:right;color:var(--faint);font-weight:600;
    padding:9px 12px;border-bottom:1px solid var(--line-2);
    text-transform:uppercase;font-size:9.5px;letter-spacing:.08em;white-space:nowrap}
  td{padding:8px 12px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}
  td.lft,th.lft{text-align:left}
  tbody tr{transition:background .1s}
  tbody tr:hover{background:var(--panel)}
  tr.dim td,td.dim{color:var(--dim)}
  .jtable-wrap{overflow:auto;border:1px solid var(--line);border-radius:var(--r)}
  .jin{background:var(--inset);border:1px solid var(--line);color:var(--txt);
    border-radius:var(--r-sm);padding:5px 8px;font:12px var(--font-mono);
    transition:border-color .15s,box-shadow .15s}
  .jin:focus{outline:none;border-color:var(--accent-dim);box-shadow:0 0 0 3px rgba(65,214,195,.12)}
  .jin.setup{width:138px} .jin.note{width:178px} .jin.miss{width:128px}
  .jin.risk{width:60px;text-align:right}
  select.jin{cursor:pointer}
  input[type=checkbox]{accent-color:var(--accent);width:15px;height:15px;cursor:pointer}
  tr.win td.pnl{color:var(--long);font-weight:600}
  tr.loss td.pnl{color:var(--short);font-weight:600}

  /* ── price chart ── */
  .chartcard{margin:16px 0 6px;max-width:600px;background:var(--panel);
    border:1px solid var(--line);border-radius:var(--r);padding:12px 14px 8px}
  .pxchart{width:100%;height:272px;display:block}
  .chartlegend{display:flex;flex-wrap:wrap;gap:6px 16px;padding:0 2px 10px;
    font-family:var(--font-ui);font-size:10.5px;color:var(--dim);letter-spacing:.02em}
  .chartlegend .lg{display:inline-flex;align-items:center;gap:6px}
  .chartlegend .lg i{width:10px;height:2px;border-radius:1px;flex:0 0 auto}
  .chartlegend .lg.ent i{background:rgba(233,238,245,.75)}
  .chartlegend .lg.sl i{background:var(--short)}
  .chartlegend .lg.tp i{background:var(--long)}

  /* ── risk ladder (R:R as proportional bar) ── */
  .ladder{margin:2px 0 14px;position:relative}
  .ladbar{position:relative;display:flex;height:11px;border-radius:6px;
    overflow:hidden;background:var(--inset);border:1px solid var(--line)}
  .lad-risk{background:linear-gradient(90deg,rgba(242,109,134,.3),var(--short))}
  .lad-reward{background:linear-gradient(90deg,var(--long),rgba(52,194,122,.3))}
  .lad-entry{position:absolute;top:-3px;bottom:-3px;width:2px;
    background:var(--txt);box-shadow:0 0 6px rgba(233,238,245,.6)}
  .ladticks{position:relative;height:13px;margin-top:6px;
    font-family:var(--font-ui);font-size:9.5px;letter-spacing:.02em}
  .ladticks span{position:absolute;white-space:nowrap}
  .ladticks .t-sl{left:0;color:var(--short)}
  .ladticks .t-tp{right:0;color:var(--long)}
  .ladticks .t-en{transform:translateX(-50%);color:var(--dim)}

  /* ── sparkline (triage rail) ── */
  .spark{width:62px;height:20px;flex:0 0 auto;margin-left:auto;opacity:.92}

  /* ── responsive ── */
  @media(max-width:760px){
    .layout{flex-direction:column}
    aside{width:100%;max-height:40vh;border-right:0;border-bottom:1px solid var(--line)}
    main{padding:20px}
    .settings{margin-left:0;width:100%}
    header{gap:12px}
  }
  /* ── a11y ── */
  :focus-visible{outline:2px solid var(--accent);outline-offset:2px}
  @media(prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
</style></head>
<body class="tab-scanner">
<header>
  <h1>S/R&nbsp;<span>ANALYZER</span></h1>
  <div class="tabs">
    <button class="tab on" id="tab-scanner">Scanner</button>
    <button class="tab" id="tab-journal">Journal</button>
  </div>
  <div class="meta scanner-only">
    <span><span id="pulse" class="pulse"></span> <b id="status">—</b></span>
    <span>scan <b id="scant">—</b></span>
    <span>nästa <b id="nextt">—</b></span>
    <span><b id="flagged">0</b> flaggade · <b id="clear">0</b> rena · <b id="failed">0</b> fel</span>
  </div>
  <div class="settings scanner-only">
    <label>konto <input id="acc" type="number" step="1" min="0"></label>
    <label>risk % <input id="risk" type="number" step="0.1" min="0"></label>
  </div>
</header>
<div class="note">Beslutsstöd — objektiva inputs + risk-geometri. Ingen riktningsdom; "om du tar nivån"-matten är geometri, inte råd. Hävstångsfärg följer din ≤3x-regel.</div>

<div class="layout scanner-view">
  <aside id="list"><div class="empty" style="padding:40px 14px">Väntar på första scan…</div></aside>
  <main id="detail"><div class="empty">Väntar på första scan…</div></main>
</div>

<div class="journal-view" id="journalView">
  <datalist id="setuplist">
    <option value="stöd-studs"><option value="motstånd-avvisning"><option value="breakout-retest"><option value="range-fade">
  </datalist>
  <div id="jbanner"></div>
  <div class="jbar">
    <div class="jstats" id="jstats"></div>
    <div class="jsync">
      <span id="jsyncinfo" class="dim"></span>
      <button id="syncBtn" class="tab">Synka nu</button>
    </div>
  </div>
  <div class="jsetups" id="jsetups"></div>
  <div class="jtable-wrap"><table class="jtable"><thead id="jhead"></thead><tbody id="jbody"></tbody></table></div>
</div>

<script>
const $=id=>document.getElementById(id);
const fmtT=ts=>ts?new Date(ts*1000).toLocaleTimeString('sv-SE',{hour:'2-digit',minute:'2-digit',second:'2-digit'}):'—';
const n=(x,d=2)=>x==null?'—':Number(x).toLocaleString('sv-SE',{minimumFractionDigits:d,maximumFractionDigits:d});
const px=x=>x==null?'—':(Math.abs(x)>=1?n(x,2):n(x,5));
const sign=x=>x>0?'+':'';
const trendCls=t=>t==='up'?'up':t==='down'?'down':'rng';
const trendTxt=t=>t==='up'?'▲ upp':t==='down'?'▼ ner':t==='range'?'≈ range':'—';
const levCls=l=>l==null?'':l<=3?'lev-g':l<=6?'lev-a':'lev-r';
const rrCls=r=>r==null?'':r>=2?'up':r>=1?'rng':'down';

let coins=[], selected=null;

function pick(sym){ selected=sym; renderList(); renderDetail(); }
window.pick=pick;

// ───── canvas charts (no libs) ─────
function _css(v){ return getComputedStyle(document.documentElement).getPropertyValue(v).trim()||v; }
function drawPriceChart(cv,c){
  const cs=c.candles||[]; if(cs.length<2) return;
  const dpr=window.devicePixelRatio||1, W=cv.clientWidth||600, H=272;
  cv.width=W*dpr; cv.height=H*dpr;
  const ctx=cv.getContext('2d'); ctx.setTransform(dpr,0,0,dpr,0,0); ctx.clearRect(0,0,W,H);
  const padL=10,padR=52,padT=14,padB=14, pw=W-padL-padR, ph=H-padT-padB;
  const sz=c.sizing;
  let lo=Infinity,hi=-Infinity;
  for(const k of cs){ hi=Math.max(hi,k[1]); lo=Math.min(lo,k[2]); }
  const ov=[c.level]; if(sz){ ov.push(sz.entry,sz.stop); if(sz.target!=null) ov.push(sz.target); }
  for(const v of ov){ if(v!=null){ hi=Math.max(hi,v); lo=Math.min(lo,v); } }
  if(hi<=lo){ hi=lo+(Math.abs(lo)*0.01||1); }
  const pad=(hi-lo)*0.08; hi+=pad; lo-=pad;
  const X=i=>padL+(i+0.5)*(pw/cs.length);
  const Y=p=>padT+(1-(p-lo)/(hi-lo))*ph;
  // grid + right price axis
  ctx.textBaseline='middle'; ctx.font='10px '+_css('--font-mono');
  for(let t=0;t<=4;t++){ const p=lo+(hi-lo)*t/4, y=Y(p);
    ctx.strokeStyle='rgba(255,255,255,.04)'; ctx.lineWidth=1;
    ctx.beginPath(); ctx.moveTo(padL,y); ctx.lineTo(padL+pw,y); ctx.stroke();
    ctx.fillStyle=_css('--faint'); ctx.textAlign='left'; ctx.fillText(px(p),padL+pw+7,y); }
  // candles
  const up=_css('--long'), dn=_css('--short');
  const cw=pw/cs.length, bw=Math.max(1.5,Math.min(7,cw*0.6));
  for(let i=0;i<cs.length;i++){ const o=cs[i][0],h=cs[i][1],l=cs[i][2],cl=cs[i][3];
    const x=X(i), col=cl>=o?up:dn; ctx.strokeStyle=col; ctx.fillStyle=col;
    ctx.lineWidth=1; ctx.beginPath(); ctx.moveTo(x,Y(h)); ctx.lineTo(x,Y(l)); ctx.stroke();
    const yo=Y(o),yc=Y(cl); ctx.fillRect(x-bw/2,Math.min(yo,yc),bw,Math.max(1,Math.abs(yc-yo))); }
  // overlay levels — thin, no text (the HTML legend carries the labels)
  const line=(p,col,dash,w)=>{ if(p==null) return; const y=Y(p);
    ctx.save(); ctx.setLineDash(dash); ctx.strokeStyle=col; ctx.lineWidth=w;
    ctx.beginPath(); ctx.moveTo(padL,y); ctx.lineTo(padL+pw,y); ctx.stroke(); ctx.restore(); };
  const sc=c.side==='support'?_css('--sup'):_css('--res');
  line(c.level,sc,[5,4],1.2);
  if(sz){ line(sz.entry,'rgba(233,238,245,.5)',[],1);
    line(sz.stop,_css('--short'),[2,4],1);
    if(sz.target!=null) line(sz.target,_css('--long'),[2,4],1); }
}
function drawSpark(cv,closes,up){
  const dpr=window.devicePixelRatio||1, W=cv.clientWidth||62, H=20;
  cv.width=W*dpr; cv.height=H*dpr;
  const ctx=cv.getContext('2d'); ctx.setTransform(dpr,0,0,dpr,0,0); ctx.clearRect(0,0,W,H);
  let lo=Math.min(...closes), hi=Math.max(...closes); if(hi<=lo) hi=lo+1;
  const X=i=>1+(i/(closes.length-1))*(W-2), Y=p=>H-2-((p-lo)/(hi-lo))*(H-4);
  ctx.beginPath(); closes.forEach((p,i)=>{ i?ctx.lineTo(X(i),Y(p)):ctx.moveTo(X(i),Y(p)); });
  ctx.strokeStyle=up?_css('--long'):_css('--short'); ctx.lineWidth=1.4;
  ctx.lineJoin='round'; ctx.stroke();
}

function renderList(){
  const el=$('list');
  if(!coins.length){ el.innerHTML='<div class="empty" style="padding:40px 14px">Inga coins nära nivå.</div>'; return; }
  el.innerHTML=coins.map(c=>{
    const sz=c.sizing, lev=sz?n(sz.leverage,1)+'x':'—', rr=sz&&sz.rr!=null?n(sz.rr,1)+'R':'';
    return `<div class="li ${c.symbol===selected?'sel':''}" onclick="pick('${c.symbol}')">
      <div class="top"><span class="dot ${c.side}"></span><span class="lsym">${c.symbol.replace('USDT','')}</span></div>
      <span class="lside">${c.side==='support'?'STÖD':'MOTST.'}</span>
      <div class="lmeta">
        <span>${n(Math.abs(c.dist_atr),2)} ATR</span>
        <span class="lev ${levCls(sz&&sz.leverage)}">${lev}</span>
        <span class="${rrCls(sz&&sz.rr)}">${rr}</span>
        <canvas class="spark"></canvas>
      </div>
    </div>`;
  }).join('');
  const cvs=el.querySelectorAll('.spark');
  coins.forEach((c,i)=>{ const cv=cvs[i];
    if(cv&&c.candles&&c.candles.length>1){ const cl=c.candles.map(k=>k[3]);
      drawSpark(cv,cl,cl[cl.length-1]>=cl[0]); }});
}

function detailHTML(c){
  const sz=c.sizing, srsi=c.stoch_rsi;
  const _lvlc=c.side==='support'?'var(--sup)':'var(--res)';
  const _lg=`<span class="lg"><i style="background:${_lvlc}"></i>nivå ${px(c.level)}</span>`
    +(sz?`<span class="lg ent"><i></i>entry ${px(sz.entry)}</span>`:'')
    +(sz?`<span class="lg sl"><i></i>SL ${px(sz.stop)}</span>`:'')
    +(sz&&sz.target!=null?`<span class="lg tp"><i></i>TP ${px(sz.target)}</span>`:'');
  let h=`<div class="dhead">
      <span class="dsym">${c.symbol.replace('USDT','')}</span>
      <span class="dpx">${px(c.close)} · ${sign(c.pcnt24h)}${n(c.pcnt24h,2)}% 24h</span>
      <span class="tag ${c.side}">${c.side==='support'?'STÖD':'MOTSTÅND'}</span>
    </div>
    <div class="chartcard"><div class="chartlegend">${_lg}</div><canvas class="pxchart"></canvas></div>
    <div class="sect"><h3>nivå</h3>
      <div class="drow"><span class="k">pris · avstånd · touch</span>
        <span class="v big">${px(c.level)} · ${n(Math.abs(c.dist_atr),2)} ATR (${sign(c.dist_pct)}${n(c.dist_pct,2)}%) · ${c.touch}×</span></div>
    </div>
    <div class="sect"><h3>struktur</h3>
      <div class="chips">
        <span class="chip">15m <b class="${trendCls(c.trend_15m)}">${trendTxt(c.trend_15m)}</b></span>
        <span class="chip">1h <b class="${trendCls(c.trend_1h)}">${trendTxt(c.trend_1h)}</b></span>
        <span class="chip">4h <b class="${trendCls(c.trend_4h)}">${trendTxt(c.trend_4h)}</b></span>`;
  if(srsi){
    const st=srsi.state==='overbought'?'OB':srsi.state==='oversold'?'OS':'';
    const cl=srsi.state==='overbought'?'down':srsi.state==='oversold'?'up':'';
    h+=`<span class="chip">StochRSI <b class="${cl}">${n(srsi.k,0)}/${n(srsi.d,0)} ${st}</b></span>`;
  }
  h+=`</div></div>
    <div class="sect"><h3>marknad</h3>
      <div class="drow"><span class="k">funding</span><span class="v ${c.funding>0?'down':'up'}">${sign(c.funding)}${n(c.funding,4)}%</span></div>
      <div class="drow"><span class="k">open interest 1h</span><span class="v ${c.oi_change_1h>0?'up':'down'}">${c.oi_change_1h==null?'—':sign(c.oi_change_1h)+n(c.oi_change_1h,2)+'%'}</span></div>
      <div class="drow"><span class="k">omsättning 24h</span><span class="v">$${n(c.turnover24h/1e6,1)}M</span></div>
    </div>
    <div class="sect"><h3>likviditet</h3>
      <div class="drow"><span class="k">buyside ↑ / sellside ↓</span><span class="v">${px(c.liq_buyside)} · ${px(c.liq_sellside)}</span></div>
    </div>`;
  if(sz){
    const _rw=Math.abs(sz.entry-sz.stop)||1, _gw=sz.target!=null?Math.abs(sz.target-sz.entry):0;
    const _rp=_rw/(_rw+_gw)*100;
    h+=`<div class="sect"><h3>risk-geometri · ${sz.long?'lång':'kort'} om du tar nivån</h3>
      <div class="ladder">
        <div class="ladbar"><div class="lad-risk" style="flex:${_rw}"></div>${sz.target!=null?`<div class="lad-reward" style="flex:${_gw}"></div>`:''}<div class="lad-entry" style="left:${_rp}%"></div></div>
        <div class="ladticks"><span class="t-sl">SL ${px(sz.stop)}</span><span class="t-en" style="left:${_rp}%">entry ${px(sz.entry)}</span><span class="t-tp">${sz.target!=null?'TP '+px(sz.target):'TP —'}</span></div>
      </div>
      <div class="drow"><span class="k">entry</span><span class="v">${px(sz.entry)}</span></div>
      <div class="drow"><span class="k">stop (SL)</span><span class="v down">${px(sz.stop)} (${n(sz.stop_pct,2)}%)</span></div>
      <div class="drow"><span class="k">mål (TP) — nästa nivå</span><span class="v up">${px(sz.target)}${sz.target_pct==null?'':' ('+sign(sz.target_pct)+n(sz.target_pct,2)+'%)'}</span></div>
      <div class="drow"><span class="k">risk / vinst · R:R</span><span class="v">−$${n(sz.risk_amount,2)} / ${sz.rr==null?'—':'+$'+n(sz.risk_amount*sz.rr,2)} · <b class="${rrCls(sz.rr)}">${sz.rr==null?'—':n(sz.rr,2)+'R'}</b></span></div>
      <div class="drow"><span class="k">qty / notional</span><span class="v">${n(sz.qty,4)} · $${n(sz.notional,1)}</span></div>
      <div class="drow"><span class="k">hävstång (regel ≤3x)</span><span class="v big"><b class="${levCls(sz.leverage)}">${n(sz.leverage,2)}x</b></span></div>
    </div>`;
  }
  return h;
}

function renderDetail(){
  const el=$('detail');
  const c=coins.find(x=>x.symbol===selected);
  if(!c){ el.innerHTML='<div class="empty">Inga coins nära nivå just nu.</div>'; return; }
  el.innerHTML=detailHTML(c);
  const cv=el.querySelector('.pxchart');
  if(cv&&c.candles&&c.candles.length) requestAnimationFrame(()=>drawPriceChart(cv,c));
}

async function tick(){
  try{
    const d=await (await fetch('/api/state')).json();
    $('status').textContent=d.scanning?'scannar…':'idle';
    $('pulse').className='pulse'+(d.scanning?' on':'');
    $('scant').textContent=fmtT(d.scan_time);
    $('nextt').textContent=fmtT(d.next_scan);
    $('flagged').textContent=d.coins.length;
    $('clear').textContent=d.clear; $('failed').textContent=d.failed;
    if(document.activeElement!==$('acc')) $('acc').value=d.account;
    if(document.activeElement!==$('risk')) $('risk').value=d.risk_pct;
    coins=d.coins;
    if(!coins.length) selected=null;
    else if(!selected || !coins.find(c=>c.symbol===selected)) selected=coins[0].symbol;
    renderList(); renderDetail();
  }catch(e){ $('status').textContent='offline'; }
}
async function saveSettings(){
  await fetch('/api/settings',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({account:parseFloat($('acc').value)||0,risk_pct:parseFloat($('risk').value)||0})});
  tick();
}
$('acc').addEventListener('change',saveSettings);
$('risk').addEventListener('change',saveSettings);
// ───── journal ─────
const setups=['stöd-studs','motstånd-avvisning','breakout-retest','range-fade'];
const trends=['','med','mot','range'];
const pnlc=v=>v>0?'win':v<0?'loss':'';
const esc=s=>(s||'').replace(/"/g,'&quot;');
const fmtDate=ms=>ms?new Date(ms).toLocaleString('sv-SE',{month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit'}):'—';

async function saveTag(order,field,value){
  const b={order_id:order}; b[field]=value;
  try{ await fetch('/api/journal/tag',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(b)}); }
  catch(e){}
  jtick();   // re-pull immediately so per-setup-typ + stats register the change at once
}
window.saveTag=saveTag;
const statBlock=(lbl,num,cls)=>`<div class="stat"><span class="lbl">${lbl}</span><span class="num ${cls||''}">${num}</span></div>`;

function renderJournal(d){
  const ov=d.stats.overall, bs=d.stats.by_setup;
  $('jbanner').innerHTML = d.has_keys ? '' :
    '<div class="banner">Ingen read-only Bybit-nyckel hittad. Lägg <b>BYBIT_API_KEY</b> + <b>BYBIT_API_SECRET</b> i <b>.env</b> (samma mapp) och starta om servern. Tills dess är journalen tom.</div>';
  const lr=d.last_result||{};
  let si=d.syncing?'synkar…':(d.last_sync?'synkad '+fmtT(d.last_sync):'ej synkad');
  if(lr&&lr.ok===false&&lr.error&&lr.error!=='no_keys') si+=' · fel: '+lr.error;
  $('jsyncinfo').textContent=si;

  $('jstats').innerHTML=
    statBlock('trades',ov.n)+
    statBlock('win-rate',ov.winrate==null?'—':n(ov.winrate,0)+'%')+
    statBlock('netto PnL','$'+n(ov.total_pnl,2),ov.total_pnl>0?'up':ov.total_pnl<0?'down':'')+
    statBlock('profit factor',ov.profit_factor==null?'—':n(ov.profit_factor,2))+
    (ov.n<20?'<div class="stat"><span class="lbl">sample</span><span class="warn">n&lt;20 · brus, inte signal</span></div>':'');

  const keys=Object.keys(bs);
  if(keys.length){
    let h='<h3>per setup-typ</h3><table><thead><tr><th class="lft">setup</th><th>n</th><th>win%</th><th>snitt PnL</th><th>snitt R</th><th>PnL</th></tr></thead><tbody>';
    for(const k of keys){const a=bs[k];
      h+=`<tr${a.n<10?' class="dim"':''}><td class="lft">${k}</td><td>${a.n}</td><td>${a.winrate==null?'—':n(a.winrate,0)+'%'}</td><td>$${n(a.avg_pnl,2)}</td><td>${a.avg_r==null?'—':n(a.avg_r,2)+'R'}</td><td>$${n(a.total_pnl,2)}</td></tr>`;}
    $('jsetups').innerHTML=h+'</tbody></table>';
  } else $('jsetups').innerHTML='';

  if($('jbody').contains(document.activeElement)) return;   // don't clobber active edit
  $('jhead').innerHTML='<tr><th class="lft">stängd</th><th class="lft">symbol</th><th>dir</th><th>in→ut</th><th>PnL</th><th>%marg</th><th class="lft">setup</th><th>trend</th><th>scan</th><th>risk$</th><th class="lft">misstag</th><th>betyg</th><th class="lft">lärdom</th></tr>';
  $('jbody').innerHTML = d.trades.length ? d.trades.map(t=>{
    const topt=trends.map(s=>`<option value="${s}" ${(t.with_trend||'')===s?'selected':''}>${s||'—'}</option>`).join('');
    const ropt=['','1','2','3','4','5'].map(s=>`<option value="${s}" ${String(t.rating||'')===s?'selected':''}>${s||'—'}</option>`).join('');
    return `<tr class="${pnlc(t.pnl)}">
      <td class="lft dim">${fmtDate(t.closed_ms)}</td>
      <td class="lft">${(t.symbol||'').replace('USDT','')}</td>
      <td class="${t.direction==='long'?'up':'down'}">${t.direction||'—'}</td>
      <td>${px(t.entry_px)}→${px(t.exit_px)}</td>
      <td class="pnl">${n(t.pnl,2)}</td>
      <td>${n(t.pnl_pct_margin,1)}%</td>
      <td class="lft"><input class="jin setup" list="setuplist" value="${esc(t.setup_type)}" onchange="saveTag('${t.order_id}','setup_type',this.value)"></td>
      <td><select class="jin" onchange="saveTag('${t.order_id}','with_trend',this.value)">${topt}</select></td>
      <td><input type="checkbox" ${t.from_scanner?'checked':''} onchange="saveTag('${t.order_id}','from_scanner',this.checked?1:0)"></td>
      <td><input class="jin risk" type="number" step="0.5" value="${t.planned_risk??''}" onchange="saveTag('${t.order_id}','planned_risk',parseFloat(this.value)||0)"></td>
      <td class="lft"><input class="jin miss" value="${esc(t.mistakes)}" placeholder="flyttad stop…" onchange="saveTag('${t.order_id}','mistakes',this.value)"></td>
      <td><select class="jin" onchange="saveTag('${t.order_id}','rating',parseInt(this.value)||0)">${ropt}</select></td>
      <td class="lft"><input class="jin note" value="${esc(t.note)}" onchange="saveTag('${t.order_id}','note',this.value)"></td>
    </tr>`;
  }).join('') : '<tr><td class="lft dim" colspan="13">Inga trades ännu. Ta en trade så dyker den upp efter nästa synk (auto var 5:e min).</td></tr>';
}

async function jtick(){
  try{ renderJournal(await (await fetch('/api/journal/state')).json()); }catch(e){}
}
$('syncBtn').addEventListener('click',async()=>{ $('jsyncinfo').textContent='synkar…';
  await fetch('/api/journal/sync',{method:'POST'}); jtick(); });

function setTab(v){
  document.body.className='tab-'+v;
  $('tab-scanner').classList.toggle('on',v==='scanner');
  $('tab-journal').classList.toggle('on',v==='journal');
  if(v==='journal') jtick();
}
$('tab-scanner').addEventListener('click',()=>setTab('scanner'));
$('tab-journal').addEventListener('click',()=>setTab('journal'));

tick(); setInterval(tick,5000);
setInterval(()=>{ if(document.body.classList.contains('tab-journal')) jtick(); },10000);
</script>
</body></html>"""


def main() -> None:
    ap = argparse.ArgumentParser(description="S/R analyzer dashboard")
    ap.add_argument("--window", action="store_true",
                    help="open the dashboard in a new console window, then exit")
    args = ap.parse_args()

    if args.window:
        # Self-spawn in a brand-new console window (works even when launched
        # headless by another tool). The child runs the server normally.
        here = os.path.dirname(os.path.abspath(__file__)) or "."
        flags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
        subprocess.Popen([sys.executable, os.path.abspath(__file__)],
                         cwd=here, creationflags=flags, close_fds=True)
        print(f"S/R Analyzer startad i ett nytt fonster -> http://{HOST}:{PORT}")
        return

    logging.basicConfig(level=logging.ERROR,
                        format="%(asctime)s %(levelname)s %(message)s")
    for noisy in ("sr_scanner", "aiohttp", "asyncio", "uvicorn",
                  "uvicorn.error", "uvicorn.access"):
        logging.getLogger(noisy).setLevel(logging.ERROR)
    print(f"S/R Analyzer  ->  http://{HOST}:{PORT}   "
          f"(open it in your browser; leave this window running)")
    uvicorn.run(app, host=HOST, port=PORT, log_level="error")


if __name__ == "__main__":
    main()
