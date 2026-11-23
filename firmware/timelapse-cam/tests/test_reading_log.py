import json
import os
import sys
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import live_view  # noqa: E402
import reading_log  # noqa: E402

T0 = 1_700_000_000  # a fixed, made-up moment (UTC)
PROBE = "28-00000000aaaa"  # fictional probe id


def test_add_is_idempotent_by_second(tmp_path):
    log = reading_log.ReadingLog(str(tmp_path / "r.db"))
    assert log.add(T0, {PROBE: 20.5}, False) is True
    assert log.add(T0 + 0.4, {PROBE: 99.0}, True) is False  # same whole second
    samples, more = log.since(None)
    assert more is False
    assert samples == [{"ts": reading_log.iso_utc(T0), "probes": {PROBE: 20.5}, "heater_on": False}]


def test_since_is_strictly_after_and_pages(tmp_path):
    log = reading_log.ReadingLog(str(tmp_path / "r.db"))
    for i in range(5):
        log.add(T0 + 60 * i, {PROBE: 20 + i}, None)
    page, more = log.since(T0 + 60, limit=2)
    assert [s["probes"][PROBE] for s in page] == [22, 23]
    assert more is True
    assert "heater_on" not in page[0]  # unknown is left out, never false
    rest, more = log.since(reading_log.parse_since(page[-1]["ts"]), limit=2)
    assert [s["probes"][PROBE] for s in rest] == [24]
    assert more is False


def test_old_rows_dropped_oldest_first(tmp_path):
    log = reading_log.ReadingLog(str(tmp_path / "r.db"), keep_s=3600)
    log.add(T0, {PROBE: 1.0})
    log.add(T0 + 1800, {PROBE: 2.0})
    log.add(T0 + 3601, {PROBE: 3.0})
    assert log.count() == 2
    assert log.oldest() == reading_log.iso_utc(T0 + 1800)


def test_rows_survive_reopen(tmp_path):
    path = str(tmp_path / "r.db")
    log = reading_log.ReadingLog(path)
    log.add(T0, {PROBE: 21.0}, True)
    log.close()
    assert reading_log.ReadingLog(path).count() == 1


def test_parse_since_needs_offset():
    assert reading_log.parse_since("2023-11-14T22:13:20Z") == T0
    assert reading_log.parse_since("2023-11-15T07:13:20+09:00") == T0
    assert reading_log.parse_since("2023-11-15T07:13:20 09:00") == T0  # '+' decoded as space
    with pytest.raises(ValueError):
        reading_log.parse_since("2023-11-14T22:13:20")
    with pytest.raises(ValueError):
        reading_log.parse_since("yesterday")


def test_take_sample_skips_empty_and_survives_errors(tmp_path):
    log = reading_log.ReadingLog(str(tmp_path / "r.db"))

    def broken():
        raise OSError("1-wire gone")

    assert reading_log.take_sample(log, lambda: {PROBE: None}, None, now=lambda: T0) is False
    assert reading_log.take_sample(log, broken, lambda: {"on": False}, now=lambda: T0) is True
    assert reading_log.take_sample(log, lambda: {PROBE: 19.5}, broken, now=lambda: T0 + 60) is True
    samples, _ = log.since(None)
    assert samples == [
        {"ts": reading_log.iso_utc(T0), "probes": {}, "heater_on": False},
        {"ts": reading_log.iso_utc(T0 + 60), "probes": {PROBE: 19.5}},
    ]


def _get(url):
    try:
        with urllib.request.urlopen(url, timeout=5) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def test_readings_endpoint(tmp_path, monkeypatch):
    log = reading_log.ReadingLog(str(tmp_path / "r.db"))
    log.add(T0, {PROBE: 20.0}, False)
    log.add(T0 + 60, {PROBE: 20.1}, True)
    monkeypatch.setattr(live_view, "readings", log)
    server = ThreadingHTTPServer(("127.0.0.1", 0), live_view.Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        code, body = _get(f"{base}/api/readings")
        assert code == 200
        assert [s["probes"][PROBE] for s in body["samples"]] == [20.0, 20.1]
        assert body["more"] is False and body["keep_days"] == 7
        assert body["oldest"] == reading_log.iso_utc(T0)
        code, body = _get(f"{base}/api/readings?since=2023-11-14T22:13:20%2B00:00&limit=5")
        assert code == 200 and [s["heater_on"] for s in body["samples"]] == [True]
        code, body = _get(f"{base}/api/readings?since=nonsense")
        assert code == 400
    finally:
        server.shutdown()
        server.server_close()


def test_readings_endpoint_without_log(monkeypatch):
    monkeypatch.setattr(live_view, "readings", None)
    server = ThreadingHTTPServer(("127.0.0.1", 0), live_view.Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        code, _ = _get(f"http://127.0.0.1:{server.server_address[1]}/api/readings")
        assert code == 503
    finally:
        server.shutdown()
        server.server_close()
