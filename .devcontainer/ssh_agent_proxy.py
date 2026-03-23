#!/usr/bin/env python3
from __future__ import annotations

import argparse
import atexit
import os
import select
import signal
import socket
import sys
import threading
from pathlib import Path


def proxy_connection(
    client: socket.socket,
    *,
    target_unix: Path | None,
    target_tcp: tuple[str, int] | None,
) -> None:
    if (target_unix is None) == (target_tcp is None):
        raise ValueError("exactly one target mode must be configured")

    if target_unix is not None:
        upstream = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        upstream.connect(os.fspath(target_unix))
    else:
        assert target_tcp is not None
        upstream = socket.create_connection(target_tcp)

    try:
        sockets = [client, upstream]
        while True:
            readable, _, _ = select.select(sockets, [], [])
            for source in readable:
                payload = source.recv(65536)
                if not payload:
                    return
                destination = upstream if source is client else client
                destination.sendall(payload)
    finally:
        try:
            upstream.close()
        finally:
            client.close()


def parse_host_port(value: str) -> tuple[str, int]:
    host, port = value.rsplit(":", 1)
    return host, int(port)


def serve(
    *,
    listen_unix: Path | None,
    listen_tcp: tuple[str, int] | None,
    target_unix: Path | None,
    target_tcp: tuple[str, int] | None,
) -> int:
    if (listen_unix is None) == (listen_tcp is None):
        raise ValueError("exactly one listen mode must be configured")

    if listen_unix is not None:
        listen_unix.parent.mkdir(parents=True, exist_ok=True)
        listen_unix.unlink(missing_ok=True)
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(os.fspath(listen_unix))
        os.chmod(listen_unix, 0o600)
    else:
        assert listen_tcp is not None
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(listen_tcp)

    server.listen()

    def cleanup() -> None:
        try:
            server.close()
        finally:
            if listen_unix is not None:
                listen_unix.unlink(missing_ok=True)

    atexit.register(cleanup)

    def stop(_signum: int, _frame: object) -> None:
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    while True:
        client, _ = server.accept()
        worker = threading.Thread(
            target=proxy_connection,
            args=(client,),
            kwargs={
                "target_unix": target_unix,
                "target_tcp": target_tcp,
            },
            daemon=True,
        )
        worker.start()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Proxy a host SSH agent socket into a stable path.")
    parser.add_argument("--listen-unix", type=Path)
    parser.add_argument("--listen-tcp")
    parser.add_argument("--target-unix", type=Path)
    parser.add_argument("--target-tcp")
    args = parser.parse_args(argv)

    listen_unix = args.listen_unix
    listen_tcp = parse_host_port(args.listen_tcp) if args.listen_tcp else None
    target_unix = args.target_unix
    target_tcp = parse_host_port(args.target_tcp) if args.target_tcp else None

    if target_unix is not None and not target_unix.is_socket():
        print(f"target socket is unavailable: {target_unix}", file=sys.stderr)
        return 1

    serve(
        listen_unix=listen_unix,
        listen_tcp=listen_tcp,
        target_unix=target_unix,
        target_tcp=target_tcp,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
