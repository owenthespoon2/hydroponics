"""Live camera view in a browser (standard library only).

Run on the Pi:  python3 live_view.py [--port 8000]

NOTE: binds 0.0.0.0 so the PC can reach it. Use on the home LAN only;
there is no authentication. Do not expose this port to the internet.

Routes: GET /  (page), GET /stream (MJPEG), GET /temp (probe JSON).
One shared rpicam-vid process feeds every viewer.
"""
import argparse
import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "pi-thermostat"))
try:
    import ds18b20
except ImportError:  # probe reader optional
    ds18b20 = None

SOI = b"\xff\xd8"
EOI = b"\xff\xd9"
FULL_MODE = "1640:1232:10"  # IMX219 binned mode with the full field of view


def build_rpicam_cmd(args):
    """Build the rpicam-vid command from parsed CLI args."""
    cmd = ["rpicam-vid", "-t", "0", "-n", "--codec", "mjpeg"]
    if args.fov == "full":
        cmd += ["--mode", FULL_MODE]
    cmd += ["--width", str(args.width), "--height", str(args.height),
            "--framerate", str(args.framerate)]
    if args.hflip:
        cmd.append("--hflip")
    if args.vflip:
        cmd.append("--vflip")
    return cmd + ["-o", "-"]


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description="Live camera view (home LAN only).")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--fov", choices=["full", "crop"], default="full",
                    help="full = 1640x1232 binned sensor mode; crop = no --mode")
    ap.add_argument("--width", type=int, default=None)
    ap.add_argument("--height", type=int, default=None)
    ap.add_argument("--framerate", type=int, default=15)
    ap.add_argument("--hflip", action="store_true")
    ap.add_argument("--vflip", action="store_true")
    args = ap.parse_args(argv)
    default_w, default_h = (1024, 768) if args.fov == "full" else (1280, 720)
    if args.width is None:
        args.width = default_w
    if args.height is None:
        args.height = default_h
    return args

PAGE = """<!doctype html>
<html><head><meta charset="utf-8"><title>hydro-pi camera</title>
<style>
body{margin:0;background:#111;color:#eee;font-family:sans-serif;text-align:center}
img{max-width:100vw;max-height:90vh;object-fit:contain}
#temp{padding:6px;font-size:1.2em}
</style></head><body>
<div id="temp">water: ...</div>
<img src="/stream" alt="live view">
<script>
async function upd(){
  try{
    const r = await fetch('/temp'); const j = await r.json();
    const parts = Object.entries(j.probes).map(([k,v]) =>
      k + ': ' + (v === null ? 'no reading' : v.toFixed(2) + ' \\u00b0C'));
    document.getElementById('temp').textContent =
      parts.length ? parts.join('   ') : 'no probes found';
  }catch(e){document.getElementById('temp').textContent='temp unavailable';}
}
upd(); setInterval(upd, 5000);
</script></body></html>
"""


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
                self.running = False  # restart on next viewer
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
            self._send(200, "text/html; charset=utf-8", PAGE.encode())
        elif path == "/temp":
            body = json.dumps({"probes": read_probes()}).encode()
            self._send(200, "application/json", body)
        elif path == "/stream":
            self._stream()
        else:
            self._send(404, "text/plain", b"not found")

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
    args = parse_args()
    camera.cmd = build_rpicam_cmd(args)
    server = ThreadingHTTPServer(("0.0.0.0", args.port), Handler)
    server.daemon_threads = True
    print(f"Serving on port {args.port} (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        camera.stop()


if __name__ == "__main__":
    main()
