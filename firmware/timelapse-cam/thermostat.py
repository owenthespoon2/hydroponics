"""Thermostat for the heater relay. Runs on the Pi, so it keeps working with the Hub off.

Target and Auto on/off are saved in thermostat.json (survive restarts). Every tick it reads the
control probe and switches the relay with hysteresis (on at target - ON_BELOW, off at
target + OFF_ABOVE) and a minimum on/off time so the relay does not chatter.

Fail-safe: heater OFF when the reading is missing, older than STALE_S, implausible
(outside PLAUSIBLE_MIN..PLAUSIBLE_MAX) or above HARD_MAX_C. A fault always switches off at once,
ignoring the minimum times. While heating, the relay's own max-on timer is refreshed every tick,
so if this thread ever dies the relay still switches itself off. Standard library only.
"""
import json
import os
import threading
import time

TARGET_MIN_C = 10.0
TARGET_MAX_C = 32.0
HARD_MAX_C = 35.0
PLAUSIBLE_MIN_C = -5.0
PLAUSIBLE_MAX_C = 60.0
ON_BELOW_C = 0.3
OFF_ABOVE_C = 0.2
MIN_SWITCH_S = 60
STALE_S = 120
TICK_S = 5


def validate(patch, current):
    """patch {'target_c'?, 'auto'?} -> new (target_c, auto). ValueError on bad input."""
    if not isinstance(patch, dict):
        raise ValueError("body must be a JSON object")
    target, auto = current
    if "target_c" in patch:
        v = patch["target_c"]
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise ValueError("target_c must be a number")
        if not TARGET_MIN_C <= v <= TARGET_MAX_C:
            raise ValueError(f"target_c must be {TARGET_MIN_C:g} to {TARGET_MAX_C:g}")
        target = round(float(v), 1)
    if "auto" in patch:
        if not isinstance(patch["auto"], bool):
            raise ValueError("auto must be true or false")
        auto = patch["auto"]
    if auto and target is None:
        raise ValueError("set target_c before switching Auto on")
    return target, auto


class Thermostat:
    def __init__(self, relay, read_temp, path=None, clock=time.monotonic,
                 min_switch_s=MIN_SWITCH_S, stale_s=STALE_S):
        self.relay = relay
        self.read_temp = read_temp  # () -> float or None
        self.path = path
        self.clock = clock
        self.min_switch_s = min_switch_s
        self.stale_s = stale_s
        self._lock = threading.RLock()
        self.target_c = None
        self.auto = False
        self._last_change = None  # clock time of the last on/off by this controller
        self._temp = None
        self._temp_at = None
        self._fault = None
        self._stop = threading.Event()
        self._load()

    def _load(self):
        if not self.path:
            return
        try:
            with open(self.path, encoding="utf-8") as f:
                saved = json.load(f)
            self.target_c, self.auto = validate(saved, (None, False))
        except (OSError, ValueError):
            self.target_c, self.auto = None, False  # unreadable file: stay off

    def _save(self):
        if not self.path:
            return
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"target_c": self.target_c, "auto": self.auto}, f)
        os.replace(tmp, self.path)

    def configure(self, patch):
        """Apply {'target_c'?, 'auto'?}, save, act at once. Raises ValueError / OSError."""
        with self._lock:
            target, auto = validate(patch, (self.target_c, self.auto))
            was_auto = self.auto
            self.target_c, self.auto = target, auto
            self._save()
            if was_auto and not auto:
                self._switch(False)
            elif auto:
                self.tick()
            return self.status()

    def manual_override(self):
        """The manual relay button was used: Auto goes off so the two never fight."""
        with self._lock:
            if self.auto:
                self.auto = False
                try:
                    self._save()
                except OSError:
                    pass

    def _switch(self, on):
        try:
            if on:
                self.relay.on()
            else:
                self.relay.off()
        except RuntimeError:
            return False
        self._last_change = self.clock()
        return True

    def _check(self, now):
        """Return the fault text, or None when the reading is usable."""
        if self._temp is None or self._temp_at is None:
            return "no sensor reading"
        if now - self._temp_at > self.stale_s:
            return "sensor reading is stale"
        if not PLAUSIBLE_MIN_C <= self._temp <= PLAUSIBLE_MAX_C:
            return "sensor reading is implausible"
        if self._temp >= HARD_MAX_C:
            return "water above the hard maximum"
        return None

    def tick(self):
        with self._lock:
            now = self.clock()
            try:
                t = self.read_temp()
            except Exception:  # noqa: BLE001 - sensor trouble is a fault, not a crash
                t = None
            if isinstance(t, (int, float)) and not isinstance(t, bool):
                self._temp, self._temp_at = float(t), now
            if not self.auto:
                self._fault = None
                return
            self._fault = self._check(now)
            heating = self.relay.status().get("on") is True
            if self._fault:
                if heating:
                    self._switch(False)
                return
            held = self._last_change is not None and now - self._last_change < self.min_switch_s
            if heating:
                if self._temp >= self.target_c + OFF_ABOVE_C and not held:
                    self._switch(False)
                else:
                    self._refresh_watchdog()
            elif self._temp <= self.target_c - ON_BELOW_C and not held:
                self._switch(True)

    def _refresh_watchdog(self):
        try:
            self.relay.on()  # re-arms the relay's max-on timer; does not count as a switch
        except RuntimeError:
            pass

    def status(self):
        with self._lock:
            now = self.clock()
            on = self.relay.status().get("on") is True
            if not self.auto:
                state = "manual-on" if on else "off"
            elif self._fault:
                state = "fault"
            else:
                state = "heating" if on else "idle"
            age = None if self._temp_at is None else int(now - self._temp_at)
            return {"target_c": self.target_c, "auto": self.auto, "state": state,
                    "fault": self._fault if self.auto else None,
                    "heater_on": on, "temp_c": self._temp, "reading_age_s": age,
                    "hard_max_c": HARD_MAX_C, "limits_c": [TARGET_MIN_C, TARGET_MAX_C]}

    def start(self):
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        while not self._stop.is_set():
            try:
                self.tick()
            except Exception:  # noqa: BLE001 - never let the loop die
                try:
                    self.relay.off()
                except Exception:  # noqa: BLE001
                    pass
            self._stop.wait(TICK_S)

    def stop(self):
        self._stop.set()
