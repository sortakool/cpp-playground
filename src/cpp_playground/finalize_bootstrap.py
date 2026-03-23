from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


class BootstrapError(RuntimeError):
    """Raised when the bootstrap finalization fails."""


def managed_env() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("MISE_IGNORED_CONFIG_PATHS", str(Path.home() / ".config" / "mise"))
    if "MISE_GLOBAL_CONFIG_FILE" not in env:
        state_dir = Path.home() / ".local" / "state" / "cpp-playground-mise"
        state_dir.mkdir(parents=True, exist_ok=True)
        global_config = state_dir / "global-config.toml"
        global_config.touch(exist_ok=True)
        env["MISE_GLOBAL_CONFIG_FILE"] = str(global_config)
    return env


def run(cmd: list[str]) -> str:
    proc = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=managed_env(),
    )
    if proc.returncode != 0:
        raise BootstrapError(
            f"command failed ({proc.returncode}): {' '.join(cmd)}\n"
            f"{proc.stdout}{proc.stderr}".strip()
        )
    return proc.stdout.strip()


def locked_install_args(lock_path: Path, command: str) -> list[str]:
    args = [command, "install"]
    if lock_path.exists():
        args.append("--locked")
    return args


def finalize() -> dict[str, str]:
    run(["mise", "trust", str(REPO_ROOT)])
    run(locked_install_args(REPO_ROOT / "pixi.lock", "pixi"))
    uv_sync = ["uv", "sync", "--group", "dev"]
    if (REPO_ROOT / "uv.lock").exists():
        uv_sync.insert(2, "--locked")
    run(uv_sync)
    return {
        "repo_root": str(REPO_ROOT),
        "pixi_lock": str((REPO_ROOT / "pixi.lock").exists()).lower(),
        "uv_lock": str((REPO_ROOT / "uv.lock").exists()).lower(),
    }


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Finalize the repo-local bootstrap state.")
    root.add_argument("--json", action="store_true", help="Print machine-readable status")
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        result = finalize()
    except BootstrapError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print("finalize-bootstrap: ok")
        print(f"repo_root={result['repo_root']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
