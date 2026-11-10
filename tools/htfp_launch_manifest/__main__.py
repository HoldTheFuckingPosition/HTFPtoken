"""Explicit regular-file input and stdout only; no verification-runner quotas."""

import os
import stat
import sys

from .checker import check_bytes, error_report, serialize


def run(arguments):
    if len(arguments) != 1 or arguments[0].startswith("-"):
        return error_report("CLI_USAGE")
    descriptor = None
    try:
        descriptor = os.open(arguments[0], os.O_RDONLY | os.O_NONBLOCK | os.O_CLOEXEC)
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            return error_report("INPUT_UNREADABLE")
        with os.fdopen(descriptor, "rb") as stream:
            descriptor = None
            raw = stream.read(65537)
    except (OSError, ValueError):
        return error_report("INPUT_UNREADABLE")
    finally:
        if descriptor is not None:
            os.close(descriptor)
    return check_bytes(raw)


def main():
    code, report = run(sys.argv[1:])
    sys.stdout.buffer.write(serialize(report))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
