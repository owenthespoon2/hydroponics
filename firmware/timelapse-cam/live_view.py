"""Live camera view in a browser (standard library only).

Run on the Pi:  python3 live_view.py [--port 8000]

NOTE: binds 0.0.0.0 so the PC can reach it. Use on the home LAN only;
there is no authentication. Do not expose this port to the internet.

Routes: GET /  (web/index.html), GET /stream (MJPEG), GET /temp (probe JSON),
GET/POST /api/camera/settings (see camera_settings.py),
POST /api/device/shutdown and /api/device/reboot (need {"confirm": true}).
One shared rpicam-vid process feeds every viewer. Settings persist in
camera-settings.json next to this script; CLI flags override it at start.
"""
import argparse
import json
import os
import signal
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "pi-thermostat"))
import camera_settings  # noqa: E402
import device_actions  # noqa: E402
import relay as relay_mod  # noqa: E402
from camera_settings import build_rpicam_cmd  # noqa: E402,F401
try:
    import ds18b20
except ImportError:  # probe reader optional
    ds18b20 = None

SOI = b"\xff\xd8"
EOI = b"\xff\xd9"
SETTINGS_PATH = os.path.join(HERE, "camera-settings.json")
INDEX_PATH = os.path.join(HERE, "web", "index.html")
settings = camera_settings.defaults()
settings_lock = threading.Lock()


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description="Live camera view (home LAN only).")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--fov", choices=["full", "crop"], default=None,
                    help="full = 1640x1232 binned sensor mode; crop = no --mode")
    ap.add_argument("--width", type=int, default=None)
    ap.add_argument("--height", type=int, default=None)
    ap.add_argument("--framerate", type=int, default=None)
    ap.add_argument("--hflip", action="store_true", default=None)
    ap.add_argument("--vflip", action="store_true", default=None)
    ap.add_argument("--relay-pin", type=int, default=5,
                    help="GPIO for relay In1 (default 5)")
    ap.add_argument("--relay-active-high", action="store_true",
                    help="relay is ON when the pin is HIGH (default: active-low)")
    ap.add_argument("--relay-max-on", type=int, default=600,
                    help="seconds before the relay switches itself off")
    return ap.parse_args(argv)


def apply_cli(values, args):
    """Return values with any CLI flags that were given laid over them."""
    values = dict(values)
    for key in ("fov", "framerate", "hflip", "vflip"):
        if getattr(args, key) is not None:
            values[key] = getattr(args, key)
    if args.width is not None or args.height is not None:
        w, h = values["resolution"].split("x")
        values["resolution"] = f"{args.width or w}x{args.height or h}"
    return values


def split_jpegs(buffer):
    """Split a byte buffer into complete JPEG frames. Returns (frames, rest)."""
    frames = []
    while True:
        start = buffer.find(SOI)
        if start < 0:
            # keep a trailing 0xFF in case the marker is split across chunks
            return frames, (b"\xff" if buffer.endswith(b"\xff") else b"")
        end = buffer.find(EOI, start + 2)
        if end < 0:
            return frames, buffer[start:]
        frames.append(buffer[start:end + 2])
        buffer = buffer[end + 2:]


def read_probes(base=None):
    """Return {probe_id: celsius or None}."""
    if ds18b20 is None:
        return {}
    base = base or ds18b20.DEFAULT_BASE
    return {p: ds18b20.read_c(p, base) for p in ds18b20.find_probes(base)}


class Camera:
    """Shared rpicam-vid process; latest frame is broadcast to all viewers."""

    def __init__(self, cmd=None):
        self.cmd = cmd
        self.cond = threading.Condition()
        self.frame = None
        self.seq = 0
        self.proc = None
        self.running = False

    def start(self):
        with self.cond:
            if self.running:
                return
            self.running = True
        self.proc = subprocess.Popen(
            self.cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        threading.Thread(target=self._pump, args=(self.proc,), daemon=True).start()

    def _pump(self, proc):
        rest = b""
        try:
            while True:
                chunk = proc.stdout.read(65536)
                if not chunk:
                    break
                frames, rest = split_jpegs(rest + chunk)
                if frames:
                    with self.cond:
                        self.frame = frames[-1]
                        self.seq += 1
                        self.cond.notify_all()
        finally:
            with self.cond:
                if self.proc is proc:  # ignore a replaced process
                    self.running = False  # restart on next viewer
                self.cond.notify_all()

    def restart(self, cmd):
        """Use a new command; viewers' loops start the new process."""
        self.cmd = cmd
        self.stop()
        with self.cond:
            self.running = False
            self.cond.notify_all()

    def next_frame(self, last_seq, timeout=5.0):
        """Block for a frame newer than last_seq. Returns (frame, seq) or (None, last_seq)."""
        with self.cond:
            self.cond.wait_for(lambda: self.seq != last_seq or not self.running,
                               timeout)
            if self.seq != last_seq:
                return self.frame, self.seq
            return None, last_seq

    def stop(self):
        proc = self.proc
        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()


camera = Camera()
relay_ctl = None  # created in main()


def _relay_off():
    """Best effort: switch relay 1 off. Never raises."""
    if relay_ctl is not None:
        try:
            relay_ctl.off()
        except RuntimeError:
            pass


def _run_device_action(name):
    _relay_off()
    try:
        device_actions.run_action(name)
    except (ValueError, OSError):
        pass


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _send(self, code, ctype, body):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/":
            try:
                with open(INDEX_PATH, "rb") as f:
                    body = f.read()
            except OSError:
                self._send(500, "text/plain", b"web/index.html missing")
                return
            self._send(200, "text/html; charset=utf-8", body)
        elif path == "/api/camera/settings":
            with settings_lock:
                body = {"schema": camera_settings.SCHEMA, "values": dict(settings)}
            self._json(200, body)
        elif path == "/api/relay":
            if relay_ctl is None:
                self._json(500, {"error": "relay not available"})
            else:
                self._json(200, relay_ctl.status())
        elif path == "/temp":
            body = json.dumps({"probes": read_probes()}).encode()
            self._send(200, "application/json", body)
        elif path == "/stream":
            self._stream()
        elif path.startswith("/api/device/") and \
                path[len("/api/device/"):] in device_actions.ACTIONS:
            self.send_response(405)
            self.send_header("Allow", "POST")
            self.send_header("Content-Length", "0")
            self.end_headers()
        else:
            self._send(404, "text/plain", b"not found")

    def _json(self, code, obj):
        self._send(code, "application/json", json.dumps(obj).encode())

    def _device_action(self, name):
        try:
            length = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(length) or b"null")
        except ValueError:
            body = None
        if not isinstance(body, dict) or body.get("confirm") is not True:
            self._json(400, {"error": 'body must be {"confirm": true}'})
            return
        camera.stop()
        _relay_off()
        self._json(202, {"status": "shutting_down" if name == "shutdown"
                         else "rebooting"})
        threading.Timer(1.0, _run_device_action, args=(name,)).start()

    def _relay_post(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(length) or b"null")
        except ValueError:
            body = None
        if not isinstance(body, dict) or not isinstance(body.get("on"), bool):
            self._json(400, {"error": 'body must be {"on": true|false}'})
            return
        if relay_ctl is None:
            self._json(500, {"error": "relay not available"})
            return
        try:
            if body["on"]:
                relay_ctl.on()
            else:
                relay_ctl.off()
        except RuntimeError as e:
            self._json(500, {"error": str(e)})
            return
        self._json(200, relay_ctl.status())

    def do_POST(self):
        path = self.path.split("?")[0]
        if path.startswith("/api/device/"):
            name = path[len("/api/device/"):]
            if name in device_actions.ACTIONS:
                self._device_action(name)
                return
        if path == "/api/relay":
            self._relay_post()
            return
        if path != "/api/camera/settings":
            self._send(404, "text/plain", b"not found")
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
            partial = json.loads(self.rfile.read(length) or b"null")
            with settings_lock:
                new = camera_settings.validate(partial, settings)
                settings.update(new)
                values = dict(settings)
            camera_settings.save(SETTINGS_PATH, values)
        except (ValueError, TypeError) as e:  # JSON errors are ValueErrors
            self._json(400, {"error": str(e)})
            return
        except OSError as e:
            self._json(500, {"error": f"could not save settings: {e}"})
            return
        camera.restart(build_rpicam_cmd(values))
        self._json(200, {"values": values})

    def _stream(self):
        try:
            camera.start()
        except OSError:
            self._send(503, "text/plain", b"camera unavailable")
            return
        self.send_response(200)
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        seq = -1
        try:
            while True:
                frame, seq = camera.next_frame(seq)
                if frame is None:
                    if not camera.running:
                        camera.start()
                    continue
                self.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\n")
                self.wfile.write(b"Content-Length: %d\r\n\r\n" % len(frame))
                self.wfile.write(frame + b"\r\n")
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass


def main():
    global relay_ctl
    args = parse_args()
    settings.update(apply_cli(camera_settings.load(SETTINGS_PATH), args))
    camera.cmd = build_rpicam_cmd(settings)
    try:
        relay_ctl = relay_mod.Relay(pin=args.relay_pin,
                                    active_low=not args.relay_active_high,
                                    max_on_s=args.relay_max_on)
    except RuntimeError as e:
        print(f"Relay unavailable: {e}", file=sys.stderr)
        sys.exit(1)
    server = ThreadingHTTPServer(("0.0.0.0", args.port), Handler)
    server.daemon_threads = True

    def on_sigterm(signum, frame):
        # shutdown() blocks until serve_forever exits, so call it off-thread
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, on_sigterm)
    print(f"Serving on port {args.port} (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        _relay_off()
        server.server_close()
        camera.stop()


if __name__ == "__main__":
    main()
