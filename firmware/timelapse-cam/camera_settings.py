"""Camera settings: schema, validation and rpicam-vid command builder.

Pure functions, no I/O except load()/save() (JSON). The web page builds its
form from SCHEMA, so adding a setting here is enough to show it in the UI.
"""
import json

FULL_MODE = "1640:1232:10"  # IMX219 binned mode with the full field of view


def _s(key, label, type_, default, min=None, max=None, step=None, choices=None):
    return {"key": key, "label": label, "type": type_, "min": min, "max": max,
            "step": step, "choices": choices, "default": default}


SCHEMA = [
    _s("fov", "Field of view", "choice", "full", choices=["full", "crop"]),
    _s("resolution", "Resolution", "choice", "1024x768",
       choices=["640x480", "1024x768", "1280x720", "1640x1232"]),
    _s("framerate", "Frame rate", "int", 15, min=1, max=30, step=1),
    _s("brightness", "Brightness", "float", 0.0, min=-1.0, max=1.0, step=0.1),
    _s("contrast", "Contrast", "float", 1.0, min=0.0, max=2.0, step=0.1),
    _s("saturation", "Saturation", "float", 1.0, min=0.0, max=2.0, step=0.1),
    _s("sharpness", "Sharpness", "float", 1.0, min=0.0, max=2.0, step=0.1),
    _s("ev", "Exposure compensation (EV)", "float", 0.0, min=-4.0, max=4.0, step=0.5),
    # Night / dark room: a fixed long shutter and gain. 0 = automatic. A video frame
    # cannot expose longer than 1/framerate, so the frame rate is lowered to fit.
    _s("shutter_ms", "Shutter (ms, 0 = auto; long for dark)", "int", 0, min=0, max=1000, step=10),
    _s("gain", "Gain (0 = auto; 4-16 for dark)", "float", 0.0, min=0.0, max=16.0, step=0.5),
    _s("awb", "White balance", "choice", "auto",
       choices=["auto", "incandescent", "tungsten", "fluorescent", "indoor",
                "daylight", "cloudy"]),
    _s("hflip", "Mirror horizontally", "bool", False),
    _s("vflip", "Flip vertically", "bool", False),
]
_BY_KEY = {item["key"]: item for item in SCHEMA}


def defaults():
    return {item["key"]: item["default"] for item in SCHEMA}


def _check(item, value):
    key, kind = item["key"], item["type"]
    if kind == "bool":
        if not isinstance(value, bool):
            raise ValueError(f"{key}: must be true or false")
        return value
    if kind == "choice":
        if value not in item["choices"]:
            raise ValueError(f"{key}: must be one of {', '.join(item['choices'])}")
        return value
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{key}: must be a number")
    if kind == "int":
        if isinstance(value, float) and not value.is_integer():
            raise ValueError(f"{key}: must be a whole number")
        value = int(value)
    else:
        value = float(value)
    if not item["min"] <= value <= item["max"]:
        raise ValueError(f"{key}: must be between {item['min']} and {item['max']}")
    return value


def validate(partial, current):
    """Return `current` updated with `partial`. Raise ValueError naming the bad key."""
    if not isinstance(partial, dict):
        raise ValueError("settings must be a JSON object")
    for key in partial:
        if key not in _BY_KEY:
            raise ValueError(f"{key}: unknown setting")
    merged = dict(current)
    for key, value in partial.items():
        merged[key] = _check(_BY_KEY[key], value)
    return merged


def effective_framerate(values):
    """The frame rate actually used: lowered so a fixed shutter fits in one frame."""
    fps = int(values["framerate"])
    shutter = int(values.get("shutter_ms") or 0)
    if shutter > 0:
        fps = min(fps, max(1, 1000 // shutter))
    return fps


def build_rpicam_cmd(values):
    """Build the rpicam-vid command from a full settings dict."""
    width, height = values["resolution"].split("x")
    cmd = ["rpicam-vid", "-t", "0", "-n", "--codec", "mjpeg"]
    if values["fov"] == "full":
        cmd += ["--mode", FULL_MODE]
    cmd += ["--width", width, "--height", height,
            "--framerate", str(effective_framerate(values)),
            "--brightness", str(values["brightness"]),
            "--contrast", str(values["contrast"]),
            "--saturation", str(values["saturation"]),
            "--sharpness", str(values["sharpness"]),
            "--ev", str(values["ev"]),
            "--awb", values["awb"]]
    shutter = int(values.get("shutter_ms") or 0)
    if shutter > 0:
        cmd += ["--shutter", str(shutter * 1000)]  # microseconds
    gain = float(values.get("gain") or 0)
    if gain > 0:
        cmd += ["--gain", str(gain)]
    if values["hflip"]:
        cmd.append("--hflip")
    if values["vflip"]:
        cmd.append("--vflip")
    return cmd + ["-o", "-"]


def load(path):
    """Load saved settings merged over defaults; bad or missing file gives defaults."""
    values = defaults()
    try:
        with open(path, encoding="utf-8") as f:
            saved = json.load(f)
        values = validate(saved, values)
    except (OSError, ValueError):
        pass
    return values


def save(path, values):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(values, f, indent=2)
