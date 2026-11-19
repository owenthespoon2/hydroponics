"""Fixed device actions (shutdown / reboot). Nothing else may be run.

Needs a sudoers rule on the Pi allowing exactly these two commands without a
password (the owner sets that up by hand).
"""
import subprocess

ACTIONS = {
    "shutdown": ["sudo", "-n", "/usr/sbin/shutdown", "-h", "now"],
    "reboot": ["sudo", "-n", "/usr/sbin/shutdown", "-r", "now"],
}


def run_action(name, runner=subprocess.run):
    """Run one of ACTIONS by name; raise ValueError for anything else."""
    if not isinstance(name, str) or name not in ACTIONS:
        raise ValueError(f"unknown action: {name!r}")
    return runner(list(ACTIONS[name]), check=False)
