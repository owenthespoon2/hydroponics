"""Print every DS18B20 probe's temperature. Read-only; does not touch the heater."""
import argparse
import sys
import time

import ds18b20


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--interval", type=float, default=2.0,
                        help="seconds between rounds (default 2)")
    parser.add_argument("--once", action="store_true", help="print one round and exit")
    parser.add_argument("--base", default=ds18b20.DEFAULT_BASE, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    probes = ds18b20.find_probes(args.base)
    if not probes:
        print("No DS18B20 probes found (check wiring and 1-Wire overlay).", file=sys.stderr)
        return 1

    while True:
        for pid in probes:
            value = ds18b20.read_c(pid, args.base)
            print(f"{pid}  {value:.2f}" if value is not None else f"{pid}  no reading")
        sys.stdout.flush()
        if args.once:
            return 0
        time.sleep(args.interval)


if __name__ == "__main__":
    sys.exit(main())
