import json
import os
import sys
import threading
import urllib.request
from http.server import ThreadingHTTPServer

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import live_view  # noqa: E402

A = b"\xff\xd8aaa\xff\xd9"
B = b"\xff\xd8bbbb\xff\xd9"


def test_split_whole_frames():
    frames, rest = live_view.split_jpegs(A + B)
    assert frames == [A, B]
    assert rest == b""


def test_split_across_chunks():
    frames, rest = live_view.split_jpegs(A + B[:4])
    assert frames == [A]
    assert rest == B[:4]
    frames, rest = live_view.split_jpegs(rest + B[4:])
    assert frames == [B]
    assert rest == b""


def test_split_junk_before_first_marker():
    frames, rest = live_view.split_jpegs(b"junkjunk" + A)
    assert frames == [A]
    assert rest == b""
    frames, rest = live_view.split_jpegs(b"only junk")
    assert frames == [] and rest == b""


def test_cmd_default_full_fov():
    cmd = live_view.build_rpicam_cmd(live_view.parse_args([]))
    assert cmd[cmd.index("--mode") + 1] == "1640:1232:10"
    assert cmd[cmd.index("--width") + 1] == "1024"
    assert cmd[cmd.index("--height") + 1] == "768"
    assert "--hflip" not in cmd and "--vflip" not in cmd


def test_cmd_crop_has_no_mode():
    cmd = live_view.build_rpicam_cmd(live_view.parse_args(["--fov", "crop"]))
    assert "--mode" not in cmd
    assert cmd[cmd.index("--width") + 1] == "1280"
    assert cmd[cmd.index("--height") + 1] == "720"


def test_cmd_flips_and_overrides():
    args = live_view.parse_args(
        ["--hflip", "--vflip", "--width", "640", "--height", "480",
         "--framerate", "10"])
    cmd = live_view.build_rpicam_cmd(args)
    assert "--hflip" in cmd and "--vflip" in cmd
    assert cmd[cmd.index("--framerate") + 1] == "10"
    assert cmd[cmd.index("--width") + 1] == "640"


def test_temp_endpoint(tmp_path, monkeypatch):
    probe = tmp_path / "28-000000000001"
    probe.mkdir()
    (probe / "temperature").write_text("21500\n")
    bad = tmp_path / "28-000000000002"
    bad.mkdir()
    (bad / "temperature").write_text("85000\n")
    monkeypatch.setattr(live_view.ds18b20, "DEFAULT_BASE", str(tmp_path))

    server = ThreadingHTTPServer(("127.0.0.1", 0), live_view.Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        url = f"http://127.0.0.1:{server.server_address[1]}/temp"
        with urllib.request.urlopen(url, timeout=5) as r:
            data = json.loads(r.read())
    finally:
        server.shutdown()
        server.server_close()
    assert data == {"probes": {"28-000000000001": 21.5, "28-000000000002": None}}
