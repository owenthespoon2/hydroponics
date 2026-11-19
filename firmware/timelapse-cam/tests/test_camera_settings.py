import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import camera_settings as cs  # noqa: E402


def test_defaults_cover_schema():
    d = cs.defaults()
    assert set(d) == {i["key"] for i in cs.SCHEMA}
    assert d["fov"] == "full" and d["resolution"] == "1024x768"
    assert d["framerate"] == 15 and d["hflip"] is False


def test_validate_ok_merges():
    cur = cs.defaults()
    out = cs.validate({"framerate": 30, "awb": "cloudy", "ev": 1, "vflip": True}, cur)
    assert out["framerate"] == 30 and out["awb"] == "cloudy"
    assert out["ev"] == 1.0 and out["vflip"] is True
    assert cur["framerate"] == 15  # input not mutated


@pytest.mark.parametrize("partial,key", [
    ({"framerate": 31}, "framerate"),
    ({"framerate": 1.5}, "framerate"),
    ({"brightness": 2}, "brightness"),
    ({"awb": "neon"}, "awb"),
    ({"resolution": "10x10"}, "resolution"),
    ({"hflip": "yes"}, "hflip"),
    ({"contrast": True}, "contrast"),
    ({"bogus": 1}, "bogus"),
])
def test_validate_rejects_and_names_key(partial, key):
    with pytest.raises(ValueError, match=key):
        cs.validate(partial, cs.defaults())


def test_build_cmd_full():
    cmd = cs.build_rpicam_cmd(cs.defaults())
    assert cmd[0] == "rpicam-vid" and cmd[-2:] == ["-o", "-"]
    assert cmd[cmd.index("--mode") + 1] == "1640:1232:10"
    assert cmd[cmd.index("--width") + 1] == "1024"
    assert cmd[cmd.index("--height") + 1] == "768"
    assert cmd[cmd.index("--awb") + 1] == "auto"
    for flag in ("--brightness", "--contrast", "--saturation", "--sharpness", "--ev"):
        assert flag in cmd
    assert "--hflip" not in cmd and "--vflip" not in cmd


def test_build_cmd_crop_and_flips():
    vals = cs.validate({"fov": "crop", "hflip": True, "vflip": True,
                        "resolution": "1280x720", "awb": "daylight"}, cs.defaults())
    cmd = cs.build_rpicam_cmd(vals)
    assert "--mode" not in cmd
    assert "--hflip" in cmd and "--vflip" in cmd
    assert cmd[cmd.index("--width") + 1] == "1280"
    assert cmd[cmd.index("--awb") + 1] == "daylight"


def test_load_save_roundtrip_and_bad_file(tmp_path):
    p = tmp_path / "s.json"
    assert cs.load(str(p)) == cs.defaults()  # missing
    vals = cs.validate({"framerate": 20}, cs.defaults())
    cs.save(str(p), vals)
    assert cs.load(str(p)) == vals
    p.write_text("not json")
    assert cs.load(str(p)) == cs.defaults()
    p.write_text(json.dumps({"framerate": 99}))
    assert cs.load(str(p)) == cs.defaults()
