from __future__ import annotations

from .bootstrap import finalize_bootstrap, main


def finalize() -> dict[str, str]:
    return finalize_bootstrap()


if __name__ == "__main__":
    raise SystemExit(main())
