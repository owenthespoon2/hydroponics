"""Relay 1 control through the `pinctrl` CLI (no extra installs).

Default wiring: relay In1 on GPIO 5, active-low (pin LOW = relay ON).
Safety: the relay is switched OFF when the object is created, a timer
switches it off by itself after max_on_s, and any failed pinctrl call
leaves the state marked OFF.
"""
import subprocess
import threading
import time


class Relay:
    def __init__(self, pin=5, active_low=True, max_on_s=600,
                 runner=subprocess.run, timer_factory=threading.Timer):
        self.pin = pin
        self.active_low = active_low
        self.max_on_s = max_on_s
        self._runner = runner
        self._timer_factory = timer_factory
        self._lock = threading.RLock()
        self._on = False
        self._timer = None
        self._deadline = None
        self.off()

    def _drive(self, level):
        """level: 'dh' (HIGH) or 'dl' (LOW). Raises RuntimeError on failure."""
        cmd = ["pinctrl", "set", str(self.pin), "op", level]
        try:
            result = self._runner(cmd, capture_output=True, text=True)
        except OSError as e:
            raise RuntimeError(f"pinctrl failed: {e}") from e
        if result is not None and getattr(result, "returncode", 0) != 0:
            raise RuntimeError(f"pinctrl exited with {result.returncode}")

    def _cancel_timer(self):
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None
        self._deadline = None

    def on(self):
        with self._lock:
            self._cancel_timer()
            try:
                self._drive("dl" if self.active_low else "dh")
            except RuntimeError:
                self._on = False
                raise
            self._on = True
            self._deadline = time.monotonic() + self.max_on_s
            self._timer = self._timer_factory(self.max_on_s, self._auto_off)
            self._timer.daemon = True
            self._timer.start()

    def off(self):
        with self._lock:
            self._cancel_timer()
            self._on = False  # failed call must still read as off
            self._drive("dh" if self.active_low else "dl")

    def _auto_off(self):
        try:
            self.off()
        except RuntimeError:
            pass

    def status(self):
        with self._lock:
            remaining = None
            if self._on and self._deadline is not None:
                remaining = max(0, int(round(self._deadline - time.monotonic())))
            return {"on": self._on, "auto_off_in_s": remaining, "pin": self.pin,
                    "active_low": self.active_low, "max_on_s": self.max_on_s}
