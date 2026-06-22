#!/usr/bin/env python3
"""
sr_journal.py — SQLite trade journal with auto-pull from Bybit (read-only).

Pulls your closed-PnL history from Bybit (signed v5 endpoint, READ-ONLY key) and
stores one row per closed position in SQLite. Execution data is filled
automatically; you add the judgement layer afterwards (setup type, with/against
HTF trend, mistakes, lesson). Re-syncing NEVER overwrites your tags.

The point is not to store rows — it's to answer, over a real sample, which of
your level setups actually have any hit-rate FOR YOU, and which mistakes cost the
most. Treat anything under ~20 trades (or ~10 per setup) as noise, not signal.

Keys come from .env (same file as the scanner):
    BYBIT_API_KEY=...        # read-only
    BYBIT_API_SECRET=...
The scanner stays keyless on the public API; only this module uses the key.
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import os
import sqlite3
import time
from typing import Any, Optional
from urllib.parse import urlencode

import aiohttp

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "journal.db")
BYBIT_BASE = "https://api.bybit.com"
RECV_WINDOW = "5000"

# auto = exchange-derived (overwritten on re-sync); tags = user-owned (preserved).
AUTO_COLS = (
    "order_id", "symbol", "direction", "raw_side", "entry_px", "exit_px",
    "qty", "notional", "leverage", "pnl", "pnl_pct_notional", "pnl_pct_margin",
    "opened_ms", "closed_ms", "duration_ms", "synced_ms",
)
TAG_COLS = ("setup_type", "with_trend", "from_scanner",
            "planned_risk", "mistakes", "rating", "note")

SCHEMA = f"""
CREATE TABLE IF NOT EXISTS trades(
  order_id TEXT PRIMARY KEY,
  symbol TEXT, direction TEXT, raw_side TEXT,
  entry_px REAL, exit_px REAL, qty REAL, notional REAL, leverage REAL,
  pnl REAL, pnl_pct_notional REAL, pnl_pct_margin REAL,
  opened_ms INTEGER, closed_ms INTEGER, duration_ms INTEGER, synced_ms INTEGER,
  setup_type TEXT, with_trend TEXT, from_scanner INTEGER,
  planned_risk REAL, mistakes TEXT, rating INTEGER, note TEXT
);
CREATE INDEX IF NOT EXISTS idx_closed ON trades(closed_ms DESC);
CREATE INDEX IF NOT EXISTS idx_setup ON trades(setup_type);
"""


# ───────────────────────────── persistence ─────────────────────────────────
def _conn(path: str = DB_PATH) -> sqlite3.Connection:
    c = sqlite3.connect(path, timeout=10.0)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    return c


def init_db(path: str = DB_PATH) -> None:
    with _conn(path) as c:
        c.executescript(SCHEMA)


def upsert_trades(rows: list[dict], path: str = DB_PATH) -> int:
    """Insert/refresh exchange fields. Tags are preserved on conflict."""
    if not rows:
        return 0
    cols = ",".join(AUTO_COLS)
    ph = ",".join("?" * len(AUTO_COLS))
    upd = ",".join(f"{c}=excluded.{c}" for c in AUTO_COLS if c != "order_id")
    sql = (f"INSERT INTO trades ({cols}) VALUES ({ph}) "
           f"ON CONFLICT(order_id) DO UPDATE SET {upd}")
    with _conn(path) as c:
        c.executemany(sql, [tuple(r.get(k) for k in AUTO_COLS) for r in rows])
    return len(rows)


def update_tags(order_id: str, tags: dict[str, Any], path: str = DB_PATH) -> bool:
    fields = {k: v for k, v in tags.items() if k in TAG_COLS}
    if not fields:
        return False
    sets = ",".join(f"{k}=?" for k in fields)
    with _conn(path) as c:
        cur = c.execute(f"UPDATE trades SET {sets} WHERE order_id=?",
                        (*fields.values(), order_id))
    return cur.rowcount > 0


def list_trades(limit: int = 300, path: str = DB_PATH) -> list[dict]:
    with _conn(path) as c:
        rows = c.execute(
            "SELECT * FROM trades ORDER BY closed_ms DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


# ───────────────────────────── analytics ───────────────────────────────────
def _agg(rows: list[dict]) -> dict:
    n = len(rows)
    if not n:
        return {"n": 0, "winrate": None, "total_pnl": 0.0, "avg_pnl": 0.0,
                "profit_factor": None, "avg_r": None}
    wins = [r for r in rows if (r["pnl"] or 0) > 0]
    gw = sum(r["pnl"] for r in wins)
    gl = sum(r["pnl"] for r in rows if (r["pnl"] or 0) <= 0)
    rs = [r["pnl"] / r["planned_risk"] for r in rows
          if r.get("planned_risk") and r["planned_risk"] > 0 and r["pnl"] is not None]
    return {
        "n": n,
        "winrate": len(wins) / n * 100.0,
        "total_pnl": sum(r["pnl"] or 0 for r in rows),
        "avg_pnl": sum(r["pnl"] or 0 for r in rows) / n,
        "profit_factor": (gw / abs(gl)) if gl < 0 else None,
        "avg_r": (sum(rs) / len(rs)) if rs else None,
    }


def analytics(path: str = DB_PATH) -> dict:
    trades = list_trades(100_000, path)
    tagged = [t for t in trades if t.get("setup_type")]
    by_setup = {
        st: _agg([t for t in tagged if t["setup_type"] == st])
        for st in sorted({t["setup_type"] for t in tagged})
    }
    return {
        "overall": _agg(trades),
        "by_setup": by_setup,
        "n_total": len(trades),
        "n_tagged": len(tagged),
    }


# ───────────────────────── Bybit signed (read-only) ─────────────────────────
def _keys() -> tuple[str, str]:
    k = os.environ.get("BYBIT_API_KEY") or os.environ.get("BYBIT_KEY") or ""
    s = os.environ.get("BYBIT_API_SECRET") or os.environ.get("BYBIT_SECRET") or ""
    return k, s


def has_keys() -> bool:
    k, s = _keys()
    return bool(k and s)


def _sign(secret: str, ts: str, key: str, qs: str) -> str:
    payload = ts + key + RECV_WINDOW + qs
    return hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()


def parse_record(r: dict) -> dict:
    """Map a Bybit closed-pnl record to a trade row.
    Bybit's `side` is the CLOSING side: Sell -> the position was Long, Buy -> Short.
    """
    entry = float(r.get("avgEntryPrice") or 0)
    exit_ = float(r.get("avgExitPrice") or 0)
    qty = float(r.get("closedSize") or r.get("qty") or 0)
    notional = float(r.get("cumEntryValue") or 0)
    lev = float(r.get("leverage") or 0)
    pnl = float(r.get("closedPnl") or 0)
    side = r.get("side", "")
    margin = notional / lev if lev else 0.0
    opened = int(r.get("createdTime") or 0)
    closed = int(r.get("updatedTime") or opened)
    return {
        "order_id": r.get("orderId"),
        "symbol": r.get("symbol"),
        "direction": "long" if side == "Sell" else "short",
        "raw_side": side,
        "entry_px": entry, "exit_px": exit_, "qty": qty,
        "notional": notional, "leverage": lev, "pnl": pnl,
        "pnl_pct_notional": (pnl / notional * 100.0) if notional else 0.0,
        "pnl_pct_margin": (pnl / margin * 100.0) if margin else 0.0,
        "opened_ms": opened, "closed_ms": closed,
        "duration_ms": max(0, closed - opened),
        "synced_ms": int(time.time() * 1000),
    }


async def _fetch_window(session: aiohttp.ClientSession, key: str, secret: str,
                        start_ms: int, end_ms: int) -> list[dict]:
    out: list[dict] = []
    cursor = ""
    for _ in range(50):  # page safety cap
        params = {"category": "linear", "limit": "100",
                  "startTime": str(start_ms), "endTime": str(end_ms)}
        if cursor:
            params["cursor"] = cursor
        qs = urlencode(params)                       # sign exactly what we send
        ts = str(int(time.time() * 1000))
        headers = {
            "X-BAPI-API-KEY": key,
            "X-BAPI-TIMESTAMP": ts,
            "X-BAPI-RECV-WINDOW": RECV_WINDOW,
            "X-BAPI-SIGN": _sign(secret, ts, key, qs),
        }
        async with session.get(f"{BYBIT_BASE}/v5/position/closed-pnl?{qs}",
                               headers=headers) as r:
            data = await r.json()
        if data.get("retCode") != 0:
            raise RuntimeError(data.get("retMsg", "bad retCode"))
        res = data["result"]
        out += res.get("list", [])
        cursor = res.get("nextPageCursor") or ""
        if not cursor:
            break
    return out


async def do_sync(days: int = 7, path: str = DB_PATH) -> dict:
    """Pull closed PnL for the last `days` (chunked into <=7d windows) and upsert.
    A failure in one window no longer aborts the rest — errors are collected and the
    sync still upserts whatever it managed to pull (reported as a partial sync)."""
    key, secret = _keys()
    if not key or not secret:
        return {"ok": False, "error": "no_keys"}
    now = int(time.time() * 1000)
    start = now - days * 86_400_000
    week = 7 * 86_400_000
    records: list[dict] = []
    errors: list[str] = []
    timeout = aiohttp.ClientTimeout(total=20.0)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        ws = start
        while ws < now:
            we = min(ws + week, now)
            try:
                records += await _fetch_window(session, key, secret, ws, we)
            except Exception as e:  # noqa: BLE001 — keep going, other windows may succeed
                errors.append(str(e))
            ws = we
    if errors and not records:
        return {"ok": False, "error": "; ".join(errors[:3])}
    rows = [parse_record(r) for r in records if r.get("orderId")]
    n = await asyncio.to_thread(upsert_trades, rows, path)
    res = {"ok": True, "pulled": len(rows), "upserted": n, "synced_ms": now}
    if errors:
        res["partial"] = True
        res["error"] = "; ".join(errors[:3])
    return res
