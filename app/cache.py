"""
Fetch cache — SQLite-based cache for fetched pages.

Reduces redundant fetches for frequently accessed URLs.
Cache entries expire after a configurable TTL.
"""
from __future__ import annotations

import hashlib
import logging
import os
import sqlite3
import time
import threading
from typing import Optional

_logger = logging.getLogger(__name__)

_DEFAULT_TTL = int(os.environ.get("FETCH_CACHE_TTL", "3600"))  # 1 hour
_DB_PATH = os.environ.get("FETCH_CACHE_DB", os.path.join(
    os.path.expanduser("~"), ".openclaw", "cache", "fetch_cache.db"
))
_MAX_SIZE_MB = int(os.environ.get("FETCH_CACHE_MAX_MB", "100"))

_lock = threading.Lock()
_conn: Optional[sqlite3.Connection] = None


def _get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is not None:
        return _conn
    with _lock:
        if _conn is not None:
            return _conn
        os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)
        _conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
        _conn.execute("PRAGMA journal_mode=WAL")
        _conn.execute("PRAGMA synchronous=NORMAL")
        _conn.execute("""
            CREATE TABLE IF NOT EXISTS cache (
                url_hash TEXT PRIMARY KEY,
                url      TEXT NOT NULL,
                html     TEXT,
                text     TEXT,
                status   INTEGER DEFAULT 0,
                engine   TEXT DEFAULT '',
                fetched  REAL NOT NULL,
                ttl      INTEGER NOT NULL
            )
        """)
        _conn.execute("CREATE INDEX IF NOT EXISTS idx_fetched ON cache(fetched)")
        _conn.commit()
        return _conn


def _url_key(url: str) -> str:
    normalized = url.rstrip("/").lower()
    return hashlib.sha256(normalized.encode()).hexdigest()[:32]


def get(url: str, ttl: int = _DEFAULT_TTL) -> Optional[dict]:
    """Return cached entry for *url* if fresh, else None."""
    try:
        conn = _get_conn()
        key = _url_key(url)
        row = conn.execute(
            "SELECT url, html, text, status, engine, fetched, ttl FROM cache WHERE url_hash = ?",
            (key,),
        ).fetchone()
        if row is None:
            return None
        fetched, entry_ttl = row[5], row[6]
        effective_ttl = min(ttl, entry_ttl)
        if time.time() - fetched > effective_ttl:
            return None
        return {
            "url": row[0], "html": row[1], "text": row[2],
            "status": row[3], "engine": row[4], "cached": True,
        }
    except Exception as exc:
        _logger.debug("cache get error: %s", exc)
        return None


def put(url: str, html: str, text: str, status: int = 200, engine: str = "", ttl: int = _DEFAULT_TTL) -> None:
    """Store a fetch result in cache."""
    try:
        conn = _get_conn()
        key = _url_key(url)
        conn.execute(
            "INSERT OR REPLACE INTO cache (url_hash, url, html, text, status, engine, fetched, ttl) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (key, url, html, text, status, engine, time.time(), ttl),
        )
        conn.commit()
    except Exception as exc:
        _logger.debug("cache put error: %s", exc)


def invalidate(url: str) -> None:
    """Remove a specific URL from cache."""
    try:
        conn = _get_conn()
        conn.execute("DELETE FROM cache WHERE url_hash = ?", (_url_key(url),))
        conn.commit()
    except Exception:
        pass


def clear_expired() -> int:
    """Remove all expired entries. Returns count of deleted rows."""
    try:
        conn = _get_conn()
        cur = conn.execute(
            "DELETE FROM cache WHERE (? - fetched) > ttl", (time.time(),)
        )
        conn.commit()
        return cur.rowcount
    except Exception:
        return 0


def stats() -> dict:
    """Return cache statistics."""
    try:
        conn = _get_conn()
        total = conn.execute("SELECT COUNT(*) FROM cache").fetchone()[0]
        now = time.time()
        fresh = conn.execute(
            "SELECT COUNT(*) FROM cache WHERE (? - fetched) <= ttl", (now,)
        ).fetchone()[0]
        # Approximate size
        page_count = conn.execute("PRAGMA page_count").fetchone()[0]
        page_size = conn.execute("PRAGMA page_size").fetchone()[0]
        size_mb = (page_count * page_size) / (1024 * 1024)
        return {
            "total_entries": total,
            "fresh_entries": fresh,
            "expired_entries": total - fresh,
            "size_mb": round(size_mb, 2),
            "db_path": _DB_PATH,
        }
    except Exception as exc:
        return {"error": str(exc)}
