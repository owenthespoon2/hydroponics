import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import reading_log  # noqa: E402
import thermostat  # noqa: E402


class FakeRelay:
    def __init__(self):
        self.is_on = False
        self.on_calls = 0

    def on(self):
        self.is_on = True
        self.on_calls += 1

    def off(self):
        self.is_on = False

    def status(self):
        return {"on": self.is_on}


class Rig:
    def __init__(self, tmp_path=None, temp=20.0):
        self.now = 1000.0
        self.temp = temp
        self.relay = FakeRelay()
        path = str(tmp_path / "t.json") if tmp_path else None
        self.path = path
        self.t = thermostat.Thermostat(self.relay, lambda: self.temp, path, clock=lambda: self.now)

    def step(self, secs=5, temp=None):
        self.now += secs
        if temp is not None:
            self.temp = temp
        self.t.tick()


def test_heats_below_and_stops_above_with_hysteresis():
    r = Rig(temp=21.0)
    r.t.configure({"target_c": 22.0, "auto": True})
    assert r.relay.is_on  # 21.0 <= 21.7
    r.step(120, 22.1)
    assert r.relay.is_on  # inside the band, stays on
    r.step(5, 22.2)
    assert not r.relay.is_on  # >= target + 0.2
    r.step(120, 21.8)
    assert not r.relay.is_on  # inside the band, stays off
    r.step(5, 21.7)
    assert r.relay.is_on


def test_min_switch_time_stops_chatter():
    r = Rig(temp=21.0)
    r.t.configure({"target_c": 22.0, "auto": True})
    r.step(10, 23.0)
    assert r.relay.is_on  # only 10 s since it switched on
    r.step(60, 23.0)
    assert not r.relay.is_on
    r.step(10, 20.0)
    assert not r.relay.is_on  # off less than 60 s
    r.step(60, 20.0)
    assert r.relay.is_on


@pytest.mark.parametrize("bad", [None, 70.0, -9.0, 35.0, 36.5])
def test_missing_implausible_or_too_hot_switches_off_at_once(bad):
    r = Rig(temp=21.0)
    r.t.configure({"target_c": 22.0, "auto": True})
    assert r.relay.is_on
    r.step(5, None)
    r.temp = bad
    r.step(5)
    if bad is None:
        r.step(130)  # reading becomes stale
    assert not r.relay.is_on
    assert r.t.status()["state"] == "fault"


def test_stale_reading_is_a_fault():
    r = Rig(temp=21.0)
    r.t.configure({"target_c": 22.0, "auto": True})
    r.temp = None
    r.step(100)
    assert r.relay.is_on  # last reading still fresh enough
    r.step(30)
    assert not r.relay.is_on
    assert "stale" in r.t.status()["fault"]


def test_target_and_auto_persist(tmp_path):
    r = Rig(tmp_path, temp=21.0)
    r.t.configure({"target_c": 24.5, "auto": True})
    again = thermostat.Thermostat(FakeRelay(), lambda: 21.0, r.path)
    assert (again.target_c, again.auto) == (24.5, True)


def test_corrupt_file_stays_off(tmp_path):
    p = tmp_path / "t.json"
    p.write_text("{nope")
    t = thermostat.Thermostat(FakeRelay(), lambda: 10.0, str(p))
    assert t.auto is False


def test_validation():
    r = Rig()
    for bad in ({"target_c": 99}, {"target_c": "hot"}, {"auto": 1}, {"auto": True}, [1]):
        with pytest.raises(ValueError):
            r.t.configure(bad)
    assert r.t.auto is False


def test_auto_off_and_manual_override_stop_auto():
    r = Rig(temp=20.0)
    r.t.configure({"target_c": 22.0, "auto": True})
    assert r.relay.is_on
    r.t.configure({"auto": False})
    assert not r.relay.is_on
    r.t.configure({"auto": True})
    r.t.manual_override()
    assert r.t.auto is False
    assert json.loads(open(r.path).read())["auto"] is False if r.path else True


def test_watchdog_refreshed_while_heating():
    r = Rig(temp=20.0)
    r.t.configure({"target_c": 22.0, "auto": True})
    before = r.relay.on_calls
    r.step(5)
    assert r.relay.on_calls == before + 1


class FakeLog:
    def __init__(self):
        self.rows = []

    def add(self, ts, probes, heater_on=None):
        self.rows.append(ts)
        return True


def test_fast_mode_switches_and_expires():
    clock = {"t": 1_700_000_000.0}
    s = reading_log.Sampler(FakeLog(), lambda: {}, None, clock=lambda: clock["t"])
    assert s.fast_status()["active"] is False
    s.start_fast(600)
    st = s.fast_status()
    assert st["active"] and st["seconds_left"] == 600 and st["every_s"] == 1
    clock["t"] += 601
    st = s.fast_status()
    assert not st["active"] and st["ended"] is not None and st["started"] is not None
    s.start_fast(99999)
    assert s.fast_status()["seconds_left"] == reading_log.FAST_MAX_S
    s.stop_fast()
    assert not s.fast_status()["active"]
