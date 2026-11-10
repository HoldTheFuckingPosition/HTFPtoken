"""Operator entry point; no daemon, RPC or wallet options."""

import argparse
from .server import make_server


def port_value(text):
    if not text.isascii() or not text.isdecimal() or not 0 <= int(text) <= 65535:
        raise argparse.ArgumentTypeError("port must be0..65535")
    return int(text)


def main():
    parser = argparse.ArgumentParser(description="Fixed local HTFP snapshot reader; no blockchain access.")
    parser.add_argument("--profile", choices=("unconfigured", "local-historical"), default="unconfigured")
    parser.add_argument("--port", type=port_value, default=0)
    args = parser.parse_args()
    with make_server(args.profile, args.port) as server:
        print("HTFP read-only API listening on http://127.0.0.1:" + str(server.server_port), flush=True)
        try:
            server.serve_forever(poll_interval=0.1)
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
