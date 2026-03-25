from __future__ import annotations

from .devcontainer import (
    ensure_ssh,
    initialize_host,
    main,
    post_create,
    smoke_ssh,
    sync_github_known_hosts,
)

__all__ = [
    "ensure_ssh",
    "initialize_host",
    "post_create",
    "smoke_ssh",
    "sync_github_known_hosts",
]


if __name__ == "__main__":
    raise SystemExit(main())
