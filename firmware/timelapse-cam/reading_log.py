"""Local reading log: the Pi keeps its own readings while the Hub (Owen's PC) is off.

A background thread samples the probes and the relay once a minute and stores
one row per sample in a small SQLite file (readings.db next to live_view.py).
Rows older than KEEP_S (7 days) are dropped, oldest first. The Hub asks for
`GET /api/readings?since=<ISO time>` when it comes back and stores what it
missed. A sample is keyed by its whole-second timestamp, so asking twice or
storing twice never makes a duplicate. Standard library only.
"""
import json
import sqlite3
import threading
import time
from datetime import datetime, timezone

KEEP_S = 7 * 24 * 3600
EVERY_S = 60
MAX_PAGE = 1000


def iso_utc(ts):
    """Whole seconds since the epoch -> '2026-11-19T10:34:00+00:00'."""
    return datetime.fromtimestamp(int(ts), timezone.utc).isoformat()


def parse_since(text):
    """ISO 8601 time with an offset ('Z' allowed) -> epoch seconds. ValueError if bad."""
    if not isinstance(text, str) or not text:
        raise ValueError("since must be an ISO 8601 time with an offset")
    t = text.strip().replace(" ", "+")  # a '+' in a query string may arrive as a space
    if t.endswith("Z"):
        t = t[:-1] + "+00:00"
    dt = datetime.fromisoformat(t)
    if dt.tzinfo is None:
        raise ValueError("since needs an offset, e.g. +09:00")
    return dt.timestamp()


class ReadingLog:
    def __init__(self, path, keep_s=KEEP_S):
        self.keep_s = keep_s
        self._lock = threading.Lock()
        self._db = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS readings ("
            " ts INTEGER PRIMARY KEY,"   # whole seconds, UTC epoch
            " probes TEXT NOT NULL,"     # JSON {probe_id: celsius or null}
            " heater_on INTEGER)"        # 1 / 0 / NULL = unknown
        )

    def add(self, ts, probes, heater_on=None):
        """Store one sample (a repeat of the same second is ignored) and drop old rows.
        Returns True when a new row was stored."""
        ts = int(ts)
        heater = None if heater_on is None else (1 if heater_on else 0)
        with self._lock:
            cur = self._db.execute(
                "INSERT OR IGNORE INTO readings (ts, probes, heater_on) VALUES (?, ?, ?)",
                (ts, json.dumps(probes, sort_keys=True), heater))
            self._db.execute("DELETE FROM readings WHERE ts < ?", (ts - self.keep_s,))
            return cur.rowcount == 1

    def since(self, since_ts=None, limit=MAX_PAGE):
        """Samples strictly after since_ts (epoch seconds), oldest first.
        Returns (samples, more) where more=True means another page is waiting."""
        limit = max(1, min(int(limit), MAX_PAGE))
        after = -1 if since_ts is None else int(since_ts)
        with self._lock:
            rows = self._db.execute(
                "SELECT ts, probes, heater_on FROM readings WHERE ts > ? ORDER BY ts LIMIT ?",
                (after, limit + 1)).fetchall()
        more = len(rows) > limit
        out = []
        for ts, probes, heater in rows[:limit]:
            sample = {"ts": iso_utc(ts), "probes": json.loads(probes)}
            if heater is not None:
                sample["heater_on"] = bool(heater)
            out.append(sample)
        return out, more

    def count(self):
        with self._lock:
            return self._db.execute("SELECT COUNT(*) FROM readings").fetchone()[0]

    def oldest(self):
        with self._lock:
            row = self._db.execute("SELECT MIN(ts) FROM readings").fetchone()
        return None if row[0] is None else iso_utc(row[0])

    def close(self):
        with self._lock:
            self._db.close()


def take_sample(log, read_probes, relay_status, now=time.time):
    """Read once and store. Skips a sample with no probe value and no relay state.
    Never raises (a bad read must not stop the logger)."""
    try:
        probes = read_probes() or {}
    except Exception:  # noqa: BLE001 - sensor trouble only skips this sample
        probes = {}
    heater = None
    try:
        status = relay_status() if relay_status else None
        if isinstance(status, dict) and isinstance(status.get("on"), bool):
            heater = status["on"]
    except Exception:  # noqa: BLE001
        heater = None
    has_value = any(isinstance(v, (int, float)) for v in probes.values())
    if not has_value and heater is None:
        return False
    try:
        return log.add(now(), probes, heater)
    except sqlite3.Error:
        return False


class Sampler:
    """Daemon thread that calls take_sample every EVERY_S seconds until stop()."""

    def __init__(self, log, read_probes, relay_status, every_s=EVERY_S):
        self.log = log
        self.read_probes = read_probes
        self.relay_status = relay_status
        self.every_s = every_s
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self._thread.start()

    def _run(self):
        while not self._stop.is_set():
            take_sample(self.log, self.read_probes, self.relay_status)
            self._stop.wait(self.every_s)

    def stop(self):
        self._stop.set()
