import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import ds18b20  # noqa: E402
import read_temp  # noqa: E402

PID = "28-000000000001"


def make(tmp_path, pid=PID, temperature=None, w1_slave=None):
    d = tmp_path / pid
    d.mkdir()
    if temperature is not None:
        (d / "temperature").write_text(temperature)
    if w1_slave is not None:
        (d / "w1_slave").write_text(w1_slave)


def w1(crc, milli):
    return f"aa bb cc : crc=00 {crc}\naa bb cc t={milli}\n"


def test_find_probes_only_28(tmp_path):
    make(tmp_path, temperature="15000\n")
    (tmp_path / "w1_bus_master1").mkdir()
    assert ds18b20.find_probes(str(tmp_path)) == [PID]


def test_find_probes_missing_base(tmp_path):
    assert ds18b20.find_probes(str(tmp_path / "nope")) == []


def test_temperature_file(tmp_path):
    make(tmp_path, temperature="15250\n")
    assert ds18b20.read_c(PID, str(tmp_path)) == 15.25


def test_w1_slave_fallback(tmp_path):
    make(tmp_path, w1_slave=w1("YES", 21500))
    assert ds18b20.read_c(PID, str(tmp_path)) == 21.5


def test_crc_no(tmp_path):
    make(tmp_path, w1_slave=w1("NO", 21500))
    assert ds18b20.read_c(PID, str(tmp_path)) is None


def test_power_on_value(tmp_path):
    make(tmp_path, temperature="85000\n")
    assert ds18b20.read_c(PID, str(tmp_path)) is None


def test_missing_probe(tmp_path):
    assert ds18b20.read_c(PID, str(tmp_path)) is None


def test_out_of_range(tmp_path):
    make(tmp_path, temperature="-20000\n")
    assert ds18b20.read_c(PID, str(tmp_path)) is None
    make(tmp_path, pid="28-000000000002", temperature="70000\n")
    assert ds18b20.read_c("28-000000000002", str(tmp_path)) is None


def test_cli_once(tmp_path, capsys):
    make(tmp_path, temperature="15000\n")
    assert read_temp.main(["--once", "--base", str(tmp_path)]) == 0
    assert capsys.readouterr().out.strip() == f"{PID}  15.00"


def test_cli_no_probes(tmp_path, capsys):
    assert read_temp.main(["--once", "--base", str(tmp_path)]) == 1
    assert "No DS18B20" in capsys.readouterr().err
