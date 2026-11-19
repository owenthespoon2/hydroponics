import json
import os
import sys
import threading
import urllib.request
from http.server import ThreadingHTTPServer

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import camera_settings  # noqa: E402
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


def test_cli_defaults_leave_saved_values():
    base = camera_settings.defaults()
    assert live_view.apply_cli(base, live_view.parse_args([])) == base


def test_cli_overrides_saved_values():
    args = live_view.parse_args(
        ["--fov", "crop", "--hflip", "--vflip", "--width", "640",
         "--height", "480", "--framerate", "10"])
    values = live_view.apply_cli(camera_settings.defaults(), args)
    assert values["fov"] == "crop"
    assert values["resolution"] == "640x480"
    assert values["framerate"] == 10
    assert values["hflip"] is True and values["vflip"] is True


def _serve(monkeypatch, tmp_path):
    monkeypatch.setattr(live_view, "SETTINGS_PATH", str(tmp_path / "s.json"))
    monkeypatch.setattr(live_view, "settings", camera_settings.defaults())
    server = ThreadingHTTPServer(("127.0.0.1", 0), live_view.Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_address[1]}"


def _post(url, body):
    req = urllib.request.Request(
        url, data=json.dumps(body).encode(), method="POST",
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def test_settings_api_get_and_post(tmp_path, monkeypatch):
    server, base = _serve(monkeypatch, tmp_path)
    cmds = []
    monkeypatch.setattr(live_view.camera, "restart", cmds.append)
    try:
        with urllib.request.urlopen(base + "/api/camera/settings", timeout=5) as r:
            data = json.loads(r.read())
        assert data["schema"] == camera_settings.SCHEMA
        assert data["values"] == camera_settings.defaults()

        status, body = _post(base + "/api/camera/settings", {"framerate": 10})
        assert status == 200 and body["values"]["framerate"] == 10
        assert len(cmds) == 1 and "--framerate" in cmds[0]
        assert camera_settings.load(str(tmp_path / "s.json"))["framerate"] == 10

        status, body = _post(base + "/api/camera/settings", {"framerate": 99})
        assert status == 400 and "framerate" in body["error"]
        status, body = _post(base + "/api/camera/settings", {"nope": 1})
        assert status == 400 and "nope" in body["error"]
        assert len(cmds) == 1
    finally:
        server.shutdown()
        server.server_close()


def test_index_served(tmp_path, monkeypatch):
    server, base = _serve(monkeypatch, tmp_path)
    try:
        with urllib.request.urlopen(base + "/", timeout=5) as r:
            html = r.read().decode()
    finally:
        server.shutdown()
        server.server_close()
    assert 'const API_BASE = "";' in html


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
