import os
import sys
import threading

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import live_view  # noqa: E402


def _fake_proc(tmp_path, pid, comm):
    d = tmp_path / str(pid)
    d.mkdir()
    (d / "comm").write_text(comm + "\n", encoding="utf-8")


def test_find_rpicam_pids(tmp_path):
    _fake_proc(tmp_path, 101, "rpicam-vid")
    _fake_proc(tmp_path, 102, "python3")
    _fake_proc(tmp_path, 103, "rpicam-vid")
    (tmp_path / "self").mkdir()
    assert sorted(live_view.find_rpicam_pids(str(tmp_path))) == [101, 103]
    assert live_view.find_rpicam_pids(str(tmp_path / "missing")) == []


def test_stop_stray_terminates_then_kills_stubborn():
    alive = {7, 8}
    sent = []

    def kill(pid, sig):
        sent.append((pid, sig))
        if sig == live_view.signal.SIGTERM and pid == 7:
            alive.discard(7)  # 7 stops politely, 8 ignores SIGTERM

    live_view.stop_stray_rpicam(find=lambda: sorted(alive), kill=kill, sleep=lambda s: None, wait_s=0.3)
    assert (7, live_view.signal.SIGTERM) in sent and (8, live_view.signal.SIGTERM) in sent
    hard = getattr(live_view.signal, "SIGKILL", live_view.signal.SIGTERM)
    assert sent[-1] == (8, hard)


class _Proc:
    def __init__(self):
        self.stdout = self
        self.done = threading.Event()

    def read(self, n):
        self.done.wait(2)
        return b""

    def poll(self):
        return 0 if self.done.is_set() else None

    def terminate(self):
        self.done.set()

    def wait(self, timeout=None):
        return 0


def test_start_is_atomic_and_ignores_replaced_process(monkeypatch):
    started = []
    monkeypatch.setattr(live_view, "stop_stray_rpicam", lambda: started.append("stray-check"))

    def popen(cmd, **kw):
        p = _Proc()
        started.append(p)
        return p

    monkeypatch.setattr(live_view.subprocess, "Popen", popen)
    cam = live_view.Camera(["rpicam-vid"])
    threads = [threading.Thread(target=cam.start) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    procs = [p for p in started if p != "stray-check"]
    assert len(procs) == 1 and started[0] == "stray-check"  # many viewers, one process
    assert cam.proc is procs[0] and cam.running
    cam.stop()
