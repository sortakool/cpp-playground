from __future__ import annotations

import argparse
import json
import os
import pwd
import shlex
import signal
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from .finalize_bootstrap import finalize

GITHUB_META_API = "https://api.github.com/meta"
DEVCONTAINER_SSHD_BIN = "/usr/sbin/sshd"
DEVCONTAINER_SSHD_DROPIN_PATH = Path("/etc/ssh/sshd_config.d/10-cpp-playground.conf")
DEVCONTAINER_SSH_AUTH_PROFILE_PATH = Path("/etc/profile.d/cpp-playground-ssh-auth-sock.sh")
DEFAULT_HOST_STATE_DIR = Path("/tmp/cpp-playground-host-state")
LOCAL_SSH_AGENT_PROXY_SOCKET = Path("/tmp/cpp-playground-ssh-agent.sock")
LOCAL_SSH_AGENT_PROXY_PID_FILE = Path("/tmp/cpp-playground-ssh-agent-proxy.pid")
HOST_SSH_AGENT_PROXY_PORT_FILE = "ssh-agent-port"
HOST_SSH_AGENT_PROXY_HOST = "host.docker.internal"


class RuntimeError_(RuntimeError):
    """Raised when the devcontainer runtime helpers fail."""


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def run(
    cmd: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None
) -> str:
    proc = subprocess.run(
        cmd,
        cwd=cwd or repo_root(),
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, **(env or {})},
    )
    if proc.returncode != 0:
        raise RuntimeError_(
            f"command failed ({proc.returncode}): {' '.join(cmd)}\n"
            f"{proc.stdout}{proc.stderr}".strip()
        )
    return proc.stdout.strip()


def current_username() -> str:
    return pwd.getpwuid(os.getuid()).pw_name


def host_state_dir() -> Path:
    return Path(os.environ.get("CPP_PLAYGROUND_HOST_STATE_DIR", str(DEFAULT_HOST_STATE_DIR)))


def ensure_socket(path: str, *, label: str) -> str:
    if not path:
        return ""
    candidate = Path(path)
    if not candidate.exists():
        raise RuntimeError_(f"{label} does not exist: {path}")
    if not candidate.is_socket():
        raise RuntimeError_(f"{label} is not a socket: {path}")
    return path


def proxy_script_path() -> Path:
    return repo_root() / ".devcontainer" / "ssh_agent_proxy.py"


def stop_container_ssh_agent_proxy() -> None:
    if LOCAL_SSH_AGENT_PROXY_PID_FILE.exists():
        try:
            pid = int(LOCAL_SSH_AGENT_PROXY_PID_FILE.read_text().strip())
        except ValueError:
            pid = 0
        if pid > 0:
            try:
                os.kill(pid, signal.SIGTERM)
            except OSError:
                pass
    LOCAL_SSH_AGENT_PROXY_PID_FILE.unlink(missing_ok=True)
    LOCAL_SSH_AGENT_PROXY_SOCKET.unlink(missing_ok=True)


def host_ssh_agent_proxy_port() -> int | None:
    port_file = host_state_dir() / HOST_SSH_AGENT_PROXY_PORT_FILE
    if not port_file.exists():
        return None
    try:
        return int(port_file.read_text().strip())
    except ValueError:
        return None


def ensure_container_ssh_agent_proxy() -> str:
    port = host_ssh_agent_proxy_port()
    if port is None:
        return ""

    if LOCAL_SSH_AGENT_PROXY_PID_FILE.exists():
        try:
            pid = int(LOCAL_SSH_AGENT_PROXY_PID_FILE.read_text().strip())
        except ValueError:
            pid = 0
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                stop_container_ssh_agent_proxy()
            else:
                try:
                    return ensure_socket(
                        str(LOCAL_SSH_AGENT_PROXY_SOCKET),
                        label="container SSH agent proxy",
                    )
                except RuntimeError_:
                    pass

    stop_container_ssh_agent_proxy()
    proc = subprocess.Popen(
        [
            sys.executable,
            str(proxy_script_path()),
            "--listen-unix",
            str(LOCAL_SSH_AGENT_PROXY_SOCKET),
            "--target-tcp",
            f"{HOST_SSH_AGENT_PROXY_HOST}:{port}",
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
        cwd=repo_root(),
    )
    LOCAL_SSH_AGENT_PROXY_PID_FILE.write_text(f"{proc.pid}\n", encoding="utf-8")

    for _ in range(50):
        if proc.poll() is not None:
            break
        try:
            return ensure_socket(
                str(LOCAL_SSH_AGENT_PROXY_SOCKET),
                label="container SSH agent proxy",
            )
        except RuntimeError_:
            time.sleep(0.1)

    stop_container_ssh_agent_proxy()
    return ""


def resolve_ssh_auth_sock() -> str:
    candidates = []
    if os.environ.get("SSH_AUTH_SOCK"):
        candidates.append(("SSH_AUTH_SOCK", os.environ["SSH_AUTH_SOCK"]))
    candidates.append(
        ("container SSH agent proxy", str(LOCAL_SSH_AGENT_PROXY_SOCKET))
    )

    for label, candidate in candidates:
        if not candidate:
            continue
        try:
            return ensure_socket(candidate, label=label)
        except RuntimeError_:
            continue
    return ensure_container_ssh_agent_proxy()


def ssh_agent_public_keys(socket_path: str) -> list[str]:
    if not socket_path:
        return []
    proc = subprocess.run(
        ["ssh-add", "-L"],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "SSH_AUTH_SOCK": socket_path},
    )
    if proc.returncode != 0:
        return []
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def fetch_json(url: str) -> dict[str, object]:
    request = urllib.request.Request(url, headers={"User-Agent": "cpp-playground/1.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = response.read().decode("utf-8")
    return json.loads(payload)


def ensure_user_ssh_paths() -> tuple[Path, Path]:
    home_dir = Path(os.environ.get("HOME", f"/home/{current_username()}"))
    ssh_dir = home_dir / ".ssh"
    ssh_dir.mkdir(mode=0o700, exist_ok=True)
    known_hosts_path = ssh_dir / "known_hosts"
    known_hosts_path.touch(mode=0o600, exist_ok=True)
    return ssh_dir, known_hosts_path


def sudo_install_text(path: Path, content: str, *, mode: int, owner: str | None = None) -> None:
    temp_path = Path("/tmp") / f"{path.name}.tmp"
    temp_path.write_text(content, encoding="utf-8")
    temp_path.chmod(mode)
    install_cmd = ["sudo", "install", "-m", f"{mode:o}"]
    if owner:
        install_cmd.extend(["-o", owner, "-g", owner])
    install_cmd.extend([str(temp_path), str(path)])
    run(install_cmd)
    temp_path.unlink(missing_ok=True)


def sync_github_known_hosts() -> None:
    _, known_hosts_path = ensure_user_ssh_paths()
    existing = [line.strip() for line in known_hosts_path.read_text().splitlines() if line.strip()]
    payload = fetch_json(GITHUB_META_API)
    ssh_keys = payload.get("ssh_keys")
    if not isinstance(ssh_keys, list) or not ssh_keys:
        raise RuntimeError_("GitHub metadata API did not return any SSH host keys")
    merged = existing[:]
    for key in ssh_keys:
        entry = f"github.com {key}"
        if entry not in merged:
            merged.append(entry)
    known_hosts_path.write_text("\n".join(merged) + "\n", encoding="utf-8")
    known_hosts_path.chmod(0o600)


def ensure_devcontainer_home_state(actual_user: str) -> None:
    home_dir = Path(os.environ.get("HOME", f"/home/{actual_user}"))
    managed_directories = [
        home_dir / ".cache",
        home_dir / ".cache" / "ccache",
        home_dir / ".cache" / "mise",
        home_dir / ".cache" / "uv",
        home_dir / ".config",
        home_dir / ".config" / "gh",
        home_dir / ".local",
        home_dir / ".local" / "bin",
        home_dir / ".local" / "share",
        home_dir / ".local" / "share" / "mise",
        home_dir / ".local" / "state",
        home_dir / ".pixi",
        home_dir / ".ssh",
    ]
    run(
        [
            "sudo",
            "install",
            "-d",
            "-o",
            actual_user,
            "-g",
            actual_user,
            *(str(path) for path in managed_directories),
        ]
    )


def sshd_running() -> bool:
    proc = subprocess.run(["pgrep", "-x", "sshd"], capture_output=True, text=True, check=False)
    return proc.returncode == 0


def ensure_ssh() -> None:
    actual_user = current_username()
    home_dir = Path(os.environ.get("HOME", f"/home/{actual_user}"))
    ssh_dir = home_dir / ".ssh"
    ssh_auth_sock = resolve_ssh_auth_sock()

    run(
        [
            "sudo",
            "install",
            "-d",
            "-m",
            "755",
            "/run/sshd",
            str(DEVCONTAINER_SSHD_DROPIN_PATH.parent),
            str(DEVCONTAINER_SSH_AUTH_PROFILE_PATH.parent),
        ]
    )
    run(["sudo", "ssh-keygen", "-A"])

    sshd_dropin = "\n".join(
        [
            "# Managed by python -m cpp_playground.devcontainer_runtime ensure-ssh",
            "Port 22",
            "PasswordAuthentication no",
            "KbdInteractiveAuthentication no",
            "PubkeyAuthentication yes",
            "PermitRootLogin no",
            "AuthorizedKeysFile .ssh/authorized_keys",
            f"AllowUsers {actual_user}",
            "",
        ]
    )
    sudo_install_text(DEVCONTAINER_SSHD_DROPIN_PATH, sshd_dropin, mode=0o644)

    if ssh_auth_sock:
        quoted_sock = shlex.quote(ssh_auth_sock)
        profile_script = "\n".join(
            [
                "#!/bin/sh",
                "# Managed by python -m cpp_playground.devcontainer_runtime ensure-ssh",
                f"if [ -S {quoted_sock} ]; then",
                f"  export SSH_AUTH_SOCK={quoted_sock}",
                "fi",
                "",
            ]
        )
        sudo_install_text(DEVCONTAINER_SSH_AUTH_PROFILE_PATH, profile_script, mode=0o644)

    public_keys = ssh_agent_public_keys(ssh_auth_sock)
    if public_keys:
        run(
            [
                "sudo",
                "install",
                "-d",
                "-o",
                actual_user,
                "-g",
                actual_user,
                "-m",
                "700",
                str(ssh_dir),
            ]
        )
        sudo_install_text(
            ssh_dir / "authorized_keys",
            "\n".join(public_keys) + "\n",
            mode=0o600,
            owner=actual_user,
        )
        print(f"synced {len(public_keys)} SSH public key(s)")
    else:
        print(
            "warning: SSH_AUTH_SOCK was unavailable or had no identities; "
            "keeping existing authorized_keys"
        )

    run(["sudo", DEVCONTAINER_SSHD_BIN, "-t"])
    if not sshd_running():
        run(["sudo", DEVCONTAINER_SSHD_BIN])
    print(f"sshd ready for {actual_user}")


def post_create() -> None:
    actual_user = current_username()
    expected_user = os.environ.get("CPP_PLAYGROUND_HOST_USER", actual_user)
    if actual_user != expected_user:
        raise RuntimeError_(
            f"expected primary devcontainer user {expected_user} but found {actual_user}"
        )
    ensure_devcontainer_home_state(actual_user)
    sync_github_known_hosts()
    finalize()
    print("post-create: ok")


def smoke_ssh_git_gh_parity() -> None:
    ssh_auth_sock = resolve_ssh_auth_sock()
    if not ssh_auth_sock:
        raise RuntimeError_("no usable SSH agent socket was found")

    ssh_env = {"SSH_AUTH_SOCK": ssh_auth_sock}
    run(["ssh-add", "-l"], env=ssh_env)

    ssh_proc = subprocess.run(
        [
            "ssh",
            "-o",
            "BatchMode=yes",
            "-o",
            "StrictHostKeyChecking=yes",
            "-T",
            "git@github.com",
        ],
        cwd=repo_root(),
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, **ssh_env},
    )
    ssh_output = f"{ssh_proc.stdout}{ssh_proc.stderr}"
    print(ssh_output, end="")
    if ssh_proc.returncode not in {0, 1} or "successfully authenticated" not in ssh_output:
        raise RuntimeError_("GitHub SSH handshake did not authenticate successfully")

    run(["git", "ls-remote", "origin"], env=ssh_env)

    gh_proc = subprocess.run(
        ["gh", "auth", "status"],
        cwd=repo_root(),
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, **ssh_env},
    )
    if gh_proc.returncode == 0:
        print(f"{gh_proc.stdout}{gh_proc.stderr}", end="")
    else:
        print(
            "warning: gh auth status is unavailable in the container; "
            "macOS keychain-backed host tokens are not forwarded",
            file=sys.stderr,
        )

    print("smoke-ssh: ok")


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Thin devcontainer runtime helpers.")
    subparsers = root.add_subparsers(dest="command", required=True)

    post_create_parser = subparsers.add_parser("post-create", help="Finalize workspace bootstrap.")
    post_create_parser.set_defaults(func=lambda: post_create())

    ensure_ssh_parser = subparsers.add_parser("ensure-ssh", help="Configure and start sshd.")
    ensure_ssh_parser.set_defaults(func=lambda: ensure_ssh())

    sync_known_hosts_parser = subparsers.add_parser(
        "sync-github-known-hosts",
        help="Seed ~/.ssh/known_hosts with GitHub SSH host keys.",
    )
    sync_known_hosts_parser.set_defaults(func=lambda: sync_github_known_hosts())

    smoke_ssh_parser = subparsers.add_parser(
        "smoke-ssh",
        help="Verify in-container SSH/git/gh parity.",
    )
    smoke_ssh_parser.set_defaults(func=lambda: smoke_ssh_git_gh_parity())
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        args.func()
    except RuntimeError_ as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
