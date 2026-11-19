"""DS18B20 reader for the Pi 1-Wire sysfs interface (standard library only)."""
import os

DEFAULT_BASE = "/sys/bus/w1/devices"
POWER_ON_MILLI = 85000
MIN_C = -10.0
MAX_C = 60.0


def find_probes(base=DEFAULT_BASE):
    """Return sorted probe ids (folders starting with '28-')."""
    try:
        names = os.listdir(base)
    except OSError:
        return []
    return sorted(n for n in names if n.startswith("28-"))


def _milli_from_temperature(path):
    try:
        with open(path, "r") as f:
            return int(f.read().strip())
    except (OSError, ValueError):
        return None


def _milli_from_w1_slave(path):
    try:
        with open(path, "r") as f:
            lines = f.read().splitlines()
    except OSError:
        return None
    if len(lines) < 2 or not lines[0].strip().endswith("YES"):
        return None
    _, sep, value = lines[1].partition("t=")
    if not sep:
        return None
    try:
        return int(value.strip())
    except ValueError:
        return None


def read_c(probe_id, base=DEFAULT_BASE):
    """Return temperature in deg C as float, or None if unavailable/invalid."""
    folder = os.path.join(base, probe_id)
    milli = _milli_from_temperature(os.path.join(folder, "temperature"))
    if milli is None:
        milli = _milli_from_w1_slave(os.path.join(folder, "w1_slave"))
    if milli is None or milli == POWER_ON_MILLI:
        return None
    celsius = milli / 1000.0
    if not (MIN_C <= celsius <= MAX_C):
        return None
    return celsius
