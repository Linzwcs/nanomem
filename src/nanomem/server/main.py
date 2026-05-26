from __future__ import annotations

import argparse

from nanomem.core.config import load_config
from nanomem.control.service import NanoMemControlService
from nanomem.service.factory import service_from_config
from nanomem.server.app import NanoMemHTTPServer
from nanomem.service.facade import ControlFacade


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="nanomem-server")
    parser.add_argument("--config", required=True, help="NanoMem config YAML/JSON path.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--max-body-bytes", type=int, default=1_000_000)
    args = parser.parse_args(argv)

    service = service_from_config(load_config(args.config))
    control_facade = ControlFacade(
        NanoMemControlService(
            store=service.store,  # type: ignore[arg-type]
            index=service.index,
        )
    )
    server = NanoMemHTTPServer(
        (args.host, args.port),
        service,
        max_body_bytes=args.max_body_bytes,
        control_facade=control_facade,
    )
    print(f"NanoMem server listening on http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
