"""CLI entrypoint. No transaction, signing, network or persistent service."""

import sys

from .codec import format_report, main


if __name__ == "__main__":
    report, exit_code = main(sys.argv[1:])
    sys.stdout.buffer.write(format_report(report))
    raise SystemExit(exit_code)
