from __future__ import annotations

import json
import os
import pty
import select
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]


class CppPlaygroundError(RuntimeError):
    """Raised when a repo automation command fails."""


@dataclass(slots=True)
class CommandResult:
    args: list[str]
    returncode: int
    stdout: str
    stderr: str

    @property
    def output(self) -> str:
        return f"{self.stdout}{self.stderr}".strip()


def repo_root() -> Path:
    return REPO_ROOT


def env_with(overrides: dict[str, str] | None = None) -> dict[str, str]:
    env = os.environ.copy()
    if overrides:
        env.update(overrides)
    return env


def run(
    args: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    check: bool = True,
    capture_output: bool = True,
    text: bool = True,
    input: str | None = None,
) -> CommandResult:
    proc = subprocess.run(
        args,
        cwd=cwd or REPO_ROOT,
        env=env_with(env),
        capture_output=capture_output,
        text=text,
        input=input,
        check=False,
    )
    result = CommandResult(
        args=list(args),
        returncode=proc.returncode,
        stdout=proc.stdout or "",
        stderr=proc.stderr or "",
    )
    if check and result.returncode != 0:
        raise CppPlaygroundError(
            f"command failed ({result.returncode}): {' '.join(args)}\n{result.output}".strip()
        )
    return result


def run_in_pty(
    args: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    check: bool = True,
) -> CommandResult:
    master_fd, slave_fd = pty.openpty()
    try:
        proc = subprocess.Popen(
            args,
            cwd=cwd or REPO_ROOT,
            env=env_with(env),
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            text=False,
        )
    finally:
        os.close(slave_fd)

    chunks: list[bytes] = []
    try:
        while True:
            ready, _, _ = select.select([master_fd], [], [], 0.1)
            if ready:
                try:
                    chunk = os.read(master_fd, 4096)
                except OSError:
                    break
                if not chunk:
                    break
                chunks.append(chunk)
                continue
            if proc.poll() is not None:
                break
    finally:
        os.close(master_fd)

    returncode = proc.wait()
    output = b"".join(chunks).decode("utf-8", errors="replace")
    result = CommandResult(
        args=list(args),
        returncode=returncode,
        stdout=output,
        stderr="",
    )
    if check and result.returncode != 0:
        raise CppPlaygroundError(
            f"command failed ({result.returncode}): {' '.join(args)}\n{result.output}".strip()
        )
    return result


def require_command(name: str) -> None:
    if not shutil_which(name):
        raise CppPlaygroundError(f"{name} is required")


def shutil_which(name: str) -> str | None:
    from shutil import which

    return which(name)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text())


def read_toml(path: Path) -> Any:
    return tomllib.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def print_json(payload: Any) -> None:
    json.dump(payload, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")


def append_github_output(values: dict[str, str]) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return
    with Path(output_path).open("a", encoding="utf-8") as handle:
        for key, value in values.items():
            handle.write(f"{key}={value}\n")
