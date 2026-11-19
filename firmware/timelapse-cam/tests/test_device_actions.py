import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import device_actions  # noqa: E402


def test_shutdown_argv():
    calls = []
    device_actions.run_action("shutdown", runner=lambda cmd, **kw: calls.append(cmd))
    assert calls == [["sudo", "-n", "/usr/sbin/shutdown", "-h", "now"]]


def test_reboot_argv():
    calls = []
    device_actions.run_action("reboot", runner=lambda cmd, **kw: calls.append(cmd))
    assert calls == [["sudo", "-n", "/usr/sbin/shutdown", "-r", "now"]]


@pytest.mark.parametrize("name", ["rm", "", None, "SHUTDOWN", "shutdown -h"])
def test_unknown_rejected(name):
    calls = []
    with pytest.raises(ValueError):
        device_actions.run_action(name, runner=lambda cmd, **kw: calls.append(cmd))
    assert calls == []
