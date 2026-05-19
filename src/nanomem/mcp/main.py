from __future__ import annotations

import argparse
import sys

from nanomem.config import load_config
from nanomem.factory import service_from_config
from nanomem.mcp.server import NanoMemMCPServer, run_stdio


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="nanomem-mcp")
    parser.add_argument(
        "--config",
        required=True,
        help="NanoMem config YAML/JSON path.",
    )
    args = parser.parse_args(argv)

    service = service_from_config(load_config(args.config))
    server = NanoMemMCPServer(service)
    run_stdio(server, input_stream=sys.stdin, output_stream=sys.stdout)
    return 0
