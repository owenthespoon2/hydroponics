import os
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import relay  # noqa: E402


class FakeRunner:
    def __init__(self, returncode=0):
        self.calls = []
        self.returncode = returncode

    def __call__(self, cmd, **kw):
        self.calls.append(cmd)
        return SimpleNamespace(returncode=self.returncode)


class FakeTimer:
    instances = []

    def __init__(self, interval, fn):
        self.interval, self.fn = interval, fn
        self.started = False
        self.cancelled = False
        self.daemon = False
        FakeTimer.instances.append(self)

    def start(self):
        self.started = True

    def cancel(self):
        self.cancelled = True


@pytest.fixture(autouse=True)
def _reset():
    FakeTimer.instances = []


def make(**kw):
    runner = FakeRunner()
    r = relay.Relay(runner=runner, timer_factory=FakeTimer, **kw)
    return r, runner


def test_off_at_construction_active_low():
    r, runner = make()
    assert runner.calls == [["pinctrl", "set", "5", "op", "dh"]]
    assert r.status()["on"] is False


def test_off_at_construction_active_high():
    r, runner = make(active_low=False)
    assert runner.calls == [["pinctrl", "set", "5", "op", "dl"]]


def test_on_off_active_low():
    r, runner = make()
    runner.calls.clear()
    r.on()
    r.off()
    assert runner.calls == [["pinctrl", "set", "5", "op", "dl"],
                            ["pinctrl", "set", "5", "op", "dh"]]


def test_on_off_active_high():
    r, runner = make(pin=7, active_low=False)
    runner.calls.clear()
    r.on()
    r.off()
    assert runner.calls == [["pinctrl", "set", "7", "op", "dh"],
                            ["pinctrl", "set", "7", "op", "dl"]]


def test_status_fields():
    r, _ = make(max_on_s=30)
    assert r.status() == {"on": False, "auto_off_in_s": None, "pin": 5,
                          "active_low": True, "max_on_s": 30}
    r.on()
    st = r.status()
    assert st["on"] is True and 0 <= st["auto_off_in_s"] <= 30


def test_timer_started_restarted_and_cancelled():
    r, _ = make(max_on_s=600)
    r.on()
    first = FakeTimer.instances[-1]
    assert first.started and first.interval == 600
    r.on()
    assert first.cancelled
    second = FakeTimer.instances[-1]
    assert second is not first and second.started
    r.off()
    assert second.cancelled


def test_auto_off_fires_and_calls_off():
    r, runner = make()
    r.on()
    runner.calls.clear()
    FakeTimer.instances[-1].fn()
    assert runner.calls == [["pinctrl", "set", "5", "op", "dh"]]
    assert r.status()["on"] is False


def test_failed_on_raises_and_stays_off():
    r, runner = make()
    runner.returncode = 1
    with pytest.raises(RuntimeError):
        r.on()
    assert r.status()["on"] is False
    assert not FakeTimer.instances


def test_failed_off_raises_and_state_off():
    r, runner = make()
    r.on()
    runner.returncode = 1
    with pytest.raises(RuntimeError):
        r.off()
    assert r.status()["on"] is False


def test_missing_pinctrl_raises():
    def boom(cmd, **kw):
        raise FileNotFoundError("pinctrl")
    with pytest.raises(RuntimeError):
        relay.Relay(runner=boom, timer_factory=FakeTimer)
