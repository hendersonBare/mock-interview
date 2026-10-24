"""Run the mock maps API: python -m mock_map [--port 8700] [--scenario FILE]."""
import argparse
import sys

from .server import MockMapServer


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="mock_map")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8700)
    parser.add_argument("--scenario", default=None, help="scenario JSON file (see DOCS.md)")
    parser.add_argument("--log-file", default=None, help="also append request log lines here")
    args = parser.parse_args(argv)
    server = MockMapServer(args.scenario, host=args.host, port=args.port, quiet=False,
                           log_file=args.log_file)
    print(f"Pathfinder mock maps API listening on {server.url}  (Ctrl+C to stop)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
