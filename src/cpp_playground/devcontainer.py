from __future__ import annotations

import argparse
import atexit
import json
import os
import pwd
import select
import shlex
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.request
from contextlib import suppress
from pathlib import Path

from .bootstrap import finalize_bootstrap
from .common import (
    CppPlaygroundError,
    env_with,
    print_json,
    repo_root,
    run,
    shutil_which,
)

GITHUB_META_API = "https://api.github.com/meta"
DEFAULT_HOST_STATE_DIR = Path.home() / ".local" / "state" / "cpp-playground"
CONTAINER_HOST_STATE_DIR = Path("/tmp/cpp-playground-host-state")
HOST_SSH_PROXY_PID_FILE = "ssh-agent-proxy.pid"
HOST_SSH_PROXY_TARGET_FILE = "ssh-agent.target"
HOST_SSH_PROXY_PORT_FILE = "ssh-agent-port"
HOST_DEVCONTAINER_RUNTIME_CONFIG_DIR = "devcontainer-runtime-{port}"
HOST_DEVCONTAINER_METADATA_FILE = "devcontainer-metadata-{port}.json"
HOST_DEVCONTAINER_LATEST_METADATA_FILE = "devcontainer-metadata-latest.json"
CONTAINER_SSH_PROXY_SOCKET = Path("/tmp/cpp-playground-ssh-agent.sock")
CONTAINER_SSH_PROXY_PID_FILE = Path("/tmp/cpp-playground-ssh-agent-proxy.pid")
DEVCONTAINER_IMAGE = "ghcr.io/ray-manaloto/cpp-devcontainer:dev"
DEVCONTAINER_BASE_CONFIG_PATH = repo_root() / ".devcontainer" / "devcontainer.json"
DEVCONTAINER_OVERRIDE_ENV_PATH = repo_root() / ".devcontainer" / "devcontainer.env"
DEVCONTAINER_INSTANCE_LABEL = "cpp-playground.devcontainer.instance"
DEVCONTAINER_NAME_PREFIX = "cpp-playground"
DEVCONTAINER_WORKSPACE_LABEL = "cpp-playground.devcontainer.workspace"
DEVCONTAINER_DEFAULT_SSH_PORT = 3333
DEVCONTAINER_USER_ENV_VAR = "CPP_PLAYGROUND_DEVCONTAINER_USER"
DEVCONTAINER_SSH_PORT_ENV_VAR = "CPP_PLAYGROUND_DEVCONTAINER_SSH_PORT"
HOST_PROXY_HOST = "host.docker.internal"
SSHD_BIN = "/usr/sbin/sshd"
SSHD_DROPIN_PATH = Path("/etc/ssh/sshd_config.d/10-cpp-playground.conf")
SSH_AUTH_PROFILE_PATH = Path("/etc/profile.d/cpp-playground-ssh-auth-sock.sh")


def host_state_dir() -> Path:
    return Path(os.environ.get("CPP_PLAYGROUND_HOST_STATE_DIR", str(DEFAULT_HOST_STATE_DIR)))


def current_username() -> str:
    return pwd.getpwuid(os.getuid()).pw_name


def workspace_basename() -> str:
    return repo_root().name


def runtime_workspace_folder() -> str:
    return f"/workspaces/{workspace_basename()}"


def devcontainer_instance_name(devcontainer_user: str, ssh_port: int) -> str:
    return f"{DEVCONTAINER_NAME_PREFIX}-{devcontainer_user}-{ssh_port}"


def devcontainer_runtime_config_path(ssh_port: int) -> Path:
    return (
        host_state_dir()
        / HOST_DEVCONTAINER_RUNTIME_CONFIG_DIR.format(port=ssh_port)
        / "devcontainer.json"
    )


def devcontainer_runtime_metadata_path(ssh_port: int) -> Path:
    return host_state_dir() / HOST_DEVCONTAINER_METADATA_FILE.format(port=ssh_port)


def devcontainer_latest_metadata_path() -> Path:
    return host_state_dir() / HOST_DEVCONTAINER_LATEST_METADATA_FILE


def parse_host_port(value: str) -> tuple[str, int]:
    host, port = value.rsplit(":", 1)
    return host, int(port)


def parse_json_trailer(text: str) -> dict[str, object]:
    for line in reversed(text.splitlines()):
        candidate = line.strip()
        if not candidate or not candidate.startswith("{"):
            continue
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    raise CppPlaygroundError("devcontainer CLI did not emit a trailing JSON result")


def parse_env_file(path: Path) -> dict[str, str]:
    overrides: dict[str, str] = {}
    if not path.exists():
        return overrides
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("export "):
            stripped = stripped.removeprefix("export ").strip()
        key, separator, value = stripped.partition("=")
        if not separator or not key or any(char.isspace() for char in key):
            raise CppPlaygroundError(f"invalid env override at {path}:{line_number}")
        parsed_value = value.strip()
        if (
            len(parsed_value) >= 2
            and parsed_value[0] == parsed_value[-1]
            and parsed_value[0] in {"'", '"'}
        ):
            parsed_value = parsed_value[1:-1]
        overrides[key] = parsed_value
    return overrides


def devcontainer_host_overrides() -> dict[str, str]:
    overrides = parse_env_file(DEVCONTAINER_OVERRIDE_ENV_PATH)
    for key in (DEVCONTAINER_USER_ENV_VAR, DEVCONTAINER_SSH_PORT_ENV_VAR):
        value = os.environ.get(key)
        if value:
            overrides[key] = value
    return overrides


def parse_tcp_port(raw_value: str, *, label: str) -> int:
    try:
        port = int(raw_value)
    except ValueError as exc:
        raise CppPlaygroundError(f"{label} must be an integer, got {raw_value!r}") from exc
    if not 1 <= port <= 65535:
        raise CppPlaygroundError(f"{label} must be in the range 1-65535, got {port}")
    return port


def resolve_requested_ssh_port(
    args: argparse.Namespace, overrides: dict[str, str]
) -> tuple[int, str]:
    if args.ssh_port is not None:
        return parse_tcp_port(str(args.ssh_port), label="--ssh-port"), "cli"
    if DEVCONTAINER_SSH_PORT_ENV_VAR in overrides:
        source = (
            DEVCONTAINER_SSH_PORT_ENV_VAR
            if DEVCONTAINER_SSH_PORT_ENV_VAR in os.environ
            else str(DEVCONTAINER_OVERRIDE_ENV_PATH)
        )
        return parse_tcp_port(overrides[DEVCONTAINER_SSH_PORT_ENV_VAR], label=source), source
    return DEVCONTAINER_DEFAULT_SSH_PORT, "default"


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


def serve_proxy(
    *,
    listen_unix: Path | None,
    listen_tcp: tuple[str, int] | None,
    target_unix: Path | None,
    target_tcp: tuple[str, int] | None,
) -> int:
    if (listen_unix is None) == (listen_tcp is None):
        raise CppPlaygroundError("exactly one listen mode must be configured")
    if (target_unix is None) == (target_tcp is None):
        raise CppPlaygroundError("exactly one target mode must be configured")

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
            kwargs={"target_unix": target_unix, "target_tcp": target_tcp},
            daemon=True,
        )
        worker.start()


def resolve_host_ssh_auth_sock() -> str:
    candidate = os.environ.get("SSH_AUTH_SOCK", "")
    if candidate and Path(candidate).is_socket():
        return candidate
    if shutil_which("launchctl"):
        launchd_sock = run(["launchctl", "getenv", "SSH_AUTH_SOCK"], check=False).stdout.strip()
        if launchd_sock and Path(launchd_sock).is_socket():
            return launchd_sock
    return ""


def choose_host_ssh_proxy_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def stop_host_ssh_proxy(state_dir: Path) -> None:
    pid_file = state_dir / HOST_SSH_PROXY_PID_FILE
    target_file = state_dir / HOST_SSH_PROXY_TARGET_FILE
    port_file = state_dir / HOST_SSH_PROXY_PORT_FILE
    if pid_file.exists():
        raw_pid = pid_file.read_text(encoding="utf-8").strip()
        if raw_pid.isdigit():
            with suppress(OSError):
                os.kill(int(raw_pid), signal.SIGTERM)
    for path in (pid_file, target_file, port_file):
        path.unlink(missing_ok=True)


def start_host_ssh_proxy(target_socket: str) -> dict[str, str]:
    state_dir = host_state_dir()
    state_dir.mkdir(parents=True, exist_ok=True)
    pid_file = state_dir / HOST_SSH_PROXY_PID_FILE
    target_file = state_dir / HOST_SSH_PROXY_TARGET_FILE
    port_file = state_dir / HOST_SSH_PROXY_PORT_FILE

    current_target = target_file.read_text(encoding="utf-8").strip() if target_file.exists() else ""
    current_port = port_file.read_text(encoding="utf-8").strip() if port_file.exists() else ""
    if pid_file.exists():
        raw_pid = pid_file.read_text(encoding="utf-8").strip()
        if raw_pid.isdigit():
            try:
                os.kill(int(raw_pid), 0)
            except OSError:
                pass
            else:
                if current_target == target_socket and current_port:
                    return {"target_socket": target_socket, "port": current_port}

    stop_host_ssh_proxy(state_dir)
    port = choose_host_ssh_proxy_port()
    target_file.write_text(target_socket + "\n", encoding="utf-8")
    port_file.write_text(f"{port}\n", encoding="utf-8")
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "cpp_playground.cli",
            "devcontainer",
            "proxy",
            "--listen-tcp",
            f"127.0.0.1:{port}",
            "--target-unix",
            target_socket,
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
        cwd=repo_root(),
        env=env_with({"PYTHONPATH": str(repo_root() / "src")}),
    )
    pid_file.write_text(f"{proc.pid}\n", encoding="utf-8")

    for _ in range(50):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.2)
            if sock.connect_ex(("127.0.0.1", port)) == 0:
                return {"target_socket": target_socket, "port": str(port)}
        if proc.poll() is not None:
            break
        time.sleep(0.1)

    stop_host_ssh_proxy(state_dir)
    raise CppPlaygroundError(f"failed to create host SSH agent proxy on 127.0.0.1:{port}")


def docker_image_exists(image: str) -> bool:
    return run(["docker", "image", "inspect", image], check=False).returncode == 0


def ensure_devcontainer_image() -> str:
    if docker_image_exists(DEVCONTAINER_IMAGE):
        return DEVCONTAINER_IMAGE
    if (
        run(
            ["docker", "pull", "--platform", "linux/amd64", DEVCONTAINER_IMAGE],
            check=False,
        ).returncode
        == 0
    ):
        return DEVCONTAINER_IMAGE
    run(["docker", "buildx", "bake", "-f", "docker-bake.hcl", "devcontainer", "--load"])
    return DEVCONTAINER_IMAGE


def initialize_host() -> dict[str, str]:
    host_user = os.environ.get("USER") or current_username()
    sock = resolve_host_ssh_auth_sock()
    if sock:
        proxy = start_host_ssh_proxy(sock)
    else:
        stop_host_ssh_proxy(host_state_dir())
        proxy = {"target_socket": "", "port": ""}

    image = ensure_devcontainer_image()
    run(
        [
            "docker",
            "buildx",
            "build",
            "--pull=false",
            "--platform",
            "linux/amd64",
            "--load",
            "--file",
            str(repo_root() / ".devcontainer" / "Dockerfile.host-user"),
            "--build-arg",
            f"BASE_IMAGE={image}",
            "--build-arg",
            f"DEVCONTAINER_USERNAME={host_user}",
            "--tag",
            image,
            str(repo_root()),
        ]
    )
    return {"image": image, "host_user": host_user, "ssh_proxy_port": proxy["port"]}


def render_devcontainer_runtime_config(
    ssh_port: int, *, devcontainer_user: str
) -> dict[str, object]:
    config = json.loads(DEVCONTAINER_BASE_CONFIG_PATH.read_text(encoding="utf-8"))
    instance_name = devcontainer_instance_name(devcontainer_user, ssh_port)
    workspace_folder = runtime_workspace_folder()

    config["name"] = instance_name
    config["remoteUser"] = devcontainer_user
    config["workspaceFolder"] = workspace_folder
    config["workspaceMount"] = (
        f"source={repo_root()},target={workspace_folder},type=bind,consistency=cached"
    )
    config["initializeCommand"] = (
        f"cd {shlex.quote(str(repo_root()))} && uv sync --locked --group dev "
        "&& uv run cpp-playground devcontainer initialize-host"
    )
    config["postCreateCommand"] = (
        f"cd {shlex.quote(workspace_folder)} && uv sync --locked --group dev "
        "&& uv run cpp-playground devcontainer post-create"
    )
    config["postStartCommand"] = (
        f"cd {shlex.quote(workspace_folder)} && uv sync --locked --group dev "
        "&& uv run cpp-playground devcontainer ensure-ssh"
    )

    container_env = dict(config.get("containerEnv", {}))
    container_env.update(
        {
            "CPP_PLAYGROUND_HOST_USER": devcontainer_user,
            "CPP_PLAYGROUND_DEVCONTAINER_IMAGE": DEVCONTAINER_IMAGE,
            "CPP_PLAYGROUND_DEVCONTAINER_NAME": instance_name,
            "CPP_PLAYGROUND_DEVCONTAINER_REMOTE_USER": devcontainer_user,
            "CPP_PLAYGROUND_DEVCONTAINER_SSH_PORT": str(ssh_port),
            "CPP_PLAYGROUND_DEVCONTAINER_WORKSPACE": workspace_folder,
            "UV_PROJECT_ENVIRONMENT": (
                f"/home/{devcontainer_user}/.local/share/cpp-playground/.venv"
            ),
        }
    )
    config["containerEnv"] = container_env

    remote_env = dict(config.get("remoteEnv", {}))
    remote_env["PATH"] = (
        "${containerEnv:PATH}"
        f":/home/{devcontainer_user}/.local/share/mise/shims"
        f":{container_env['UV_PROJECT_ENVIRONMENT']}/bin"
        f":{workspace_folder}/.pixi/envs/default/bin"
    )
    remote_env["SSH_AUTH_SOCK"] = str(CONTAINER_SSH_PROXY_SOCKET)
    config["remoteEnv"] = remote_env

    static_run_args = [
        arg
        for arg in config.get("runArgs", [])
        if not (
            arg.startswith("--name=")
            or arg.startswith("--hostname=")
            or arg.startswith("--publish=")
            or arg.startswith("--label=cpp-playground.devcontainer.")
        )
    ]
    config["runArgs"] = [
        *static_run_args,
        f"--name={instance_name}",
        f"--hostname={instance_name}",
        f"--label=cpp-playground.devcontainer.image={DEVCONTAINER_IMAGE}",
        f"--label=cpp-playground.devcontainer.instance={instance_name}",
        f"--label=cpp-playground.devcontainer.remote-user={devcontainer_user}",
        f"--label=cpp-playground.devcontainer.ssh-port={ssh_port}",
        f"--label={DEVCONTAINER_WORKSPACE_LABEL}={workspace_folder}",
        f"--publish=127.0.0.1:{ssh_port}:22",
    ]
    return config


def write_devcontainer_runtime_metadata(metadata: dict[str, object]) -> None:
    state_dir = host_state_dir()
    state_dir.mkdir(parents=True, exist_ok=True)
    raw_ssh_port = metadata.get("ssh_port")
    if not isinstance(raw_ssh_port, int | str):
        raise CppPlaygroundError("runtime metadata is missing a usable ssh_port")
    ssh_port = int(raw_ssh_port)
    devcontainer_runtime_metadata_path(ssh_port).write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    devcontainer_latest_metadata_path().write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def load_devcontainer_runtime_metadata(ssh_port: int | None = None) -> dict[str, object]:
    path = (
        devcontainer_runtime_metadata_path(ssh_port)
        if ssh_port is not None
        else devcontainer_latest_metadata_path()
    )
    if not path.exists():
        raise CppPlaygroundError(f"no recorded devcontainer runtime metadata at {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise CppPlaygroundError(f"invalid runtime metadata payload in {path}")
    return payload


def inspect_container_runtime(container_ref: str) -> dict[str, object]:
    payload = json.loads(run(["docker", "inspect", container_ref]).stdout)
    if not isinstance(payload, list) or not payload:
        raise CppPlaygroundError(f"docker inspect returned no data for {container_ref}")
    record = payload[0]
    port_binding = (record.get("NetworkSettings", {}).get("Ports", {}) or {}).get("22/tcp") or []
    first_binding = port_binding[0] if port_binding else {}
    labels = record.get("Config", {}).get("Labels", {}) or {}
    env_entries = record.get("Config", {}).get("Env", []) or []
    env_map: dict[str, str] = {}
    for entry in env_entries:
        if "=" not in entry:
            continue
        key, value = entry.split("=", 1)
        env_map[key] = value
    return {
        "container_id": record.get("Id", ""),
        "container_name": str(record.get("Name", "")).removeprefix("/"),
        "hostname": record.get("Config", {}).get("Hostname", ""),
        "host_ip": first_binding.get("HostIp", ""),
        "host_port": first_binding.get("HostPort", ""),
        "labels": labels,
        "env": env_map,
        "state": record.get("State", {}).get("Status", ""),
    }


def validate_container_runtime(metadata: dict[str, object]) -> dict[str, object]:
    runtime = inspect_container_runtime(str(metadata["container_id"]))
    expected_name = str(metadata["container_name"])
    expected_port = str(metadata["ssh_port"])
    expected_user = str(metadata["remote_user"])
    expected_workspace = str(metadata["workspace_folder"])

    if runtime["container_name"] != expected_name:
        raise CppPlaygroundError(
            f"container name mismatch: expected {expected_name}, found {runtime['container_name']}"
        )
    if runtime["hostname"] != expected_name:
        raise CppPlaygroundError(
            f"hostname mismatch: expected {expected_name}, found {runtime['hostname']}"
        )
    if runtime["host_ip"] != "127.0.0.1" or runtime["host_port"] != expected_port:
        raise CppPlaygroundError(
            f"SSH port mapping mismatch: expected 127.0.0.1:{expected_port}->22, "
            f"found {runtime['host_ip']}:{runtime['host_port']}->22"
        )
    labels_raw = runtime["labels"]
    if not isinstance(labels_raw, dict):
        raise CppPlaygroundError("docker inspect did not return a labels mapping")
    labels = {str(key): str(value) for key, value in labels_raw.items()}
    if labels.get("cpp-playground.devcontainer.instance") != expected_name:
        raise CppPlaygroundError("container instance label does not match runtime name")
    if labels.get("cpp-playground.devcontainer.remote-user") != expected_user:
        raise CppPlaygroundError("container remote-user label does not match runtime user")
    if labels.get("cpp-playground.devcontainer.ssh-port") != expected_port:
        raise CppPlaygroundError("container ssh-port label does not match runtime port")
    if labels.get(DEVCONTAINER_WORKSPACE_LABEL) != expected_workspace:
        raise CppPlaygroundError("container workspace label does not match runtime workspace")
    env_raw = runtime["env"]
    if not isinstance(env_raw, dict):
        raise CppPlaygroundError("docker inspect did not return an env mapping")
    env_map = {str(key): str(value) for key, value in env_raw.items()}
    if env_map.get("CPP_PLAYGROUND_DEVCONTAINER_NAME") != expected_name:
        raise CppPlaygroundError("container runtime env name does not match runtime metadata")
    if env_map.get("CPP_PLAYGROUND_DEVCONTAINER_REMOTE_USER") != expected_user:
        raise CppPlaygroundError("container runtime env user does not match runtime metadata")
    if env_map.get("CPP_PLAYGROUND_DEVCONTAINER_SSH_PORT") != expected_port:
        raise CppPlaygroundError("container runtime env port does not match runtime metadata")
    if env_map.get("CPP_PLAYGROUND_DEVCONTAINER_WORKSPACE") != expected_workspace:
        raise CppPlaygroundError("container runtime env workspace does not match runtime metadata")
    return runtime


def validate_host_ssh_target(metadata: dict[str, object]) -> dict[str, object]:
    socket_path = resolve_host_ssh_auth_sock()
    if not socket_path:
        raise CppPlaygroundError("host SSH_AUTH_SOCK is unavailable; cannot validate SSH target")
    ssh_port = str(metadata["ssh_port"])
    known_hosts_path = host_state_dir() / f"devcontainer-known-hosts-{ssh_port}"
    remote_command = (
        f"cd {shlex.quote(str(metadata['workspace_folder']))} "
        "&& hostname "
        "&& uv run cpp-playground devcontainer smoke-ssh"
    )
    result = run(
        [
            "ssh",
            "-o",
            "BatchMode=yes",
            "-o",
            "StrictHostKeyChecking=accept-new",
            "-o",
            f"UserKnownHostsFile={known_hosts_path}",
            "-p",
            ssh_port,
            f"{metadata['remote_user']}@127.0.0.1",
            remote_command,
        ],
        env={"SSH_AUTH_SOCK": socket_path},
        check=False,
    )
    if result.returncode != 0:
        raise CppPlaygroundError(
            f"failed to validate SSH target on 127.0.0.1:{ssh_port}\n{result.output}"
        )
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if not lines:
        raise CppPlaygroundError("SSH validation produced no stdout")
    if lines[0] != metadata["container_name"]:
        raise CppPlaygroundError(
            f"SSH landed in {lines[0]} instead of {metadata['container_name']}"
        )
    return {
        "known_hosts": str(known_hosts_path),
        "hostname": lines[0],
        "validated_command": remote_command,
    }


def repo_devcontainer_container_ids(workspace_folder: str) -> list[str]:
    result = run(
        [
            "docker",
            "ps",
            "-aq",
            "--filter",
            f"label={DEVCONTAINER_WORKSPACE_LABEL}={workspace_folder}",
        ]
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def remove_repo_devcontainer_instances(workspace_folder: str) -> list[str]:
    container_ids = repo_devcontainer_container_ids(workspace_folder)
    if not container_ids:
        return []
    run(["docker", "rm", "-f", *container_ids])
    return container_ids


def devcontainer_up(args: argparse.Namespace) -> dict[str, object]:
    host_user = os.environ.get("USER") or current_username()
    overrides = devcontainer_host_overrides()
    devcontainer_user = (
        args.devcontainer_user or overrides.get(DEVCONTAINER_USER_ENV_VAR) or host_user
    )
    ssh_port, ssh_port_source = resolve_requested_ssh_port(args, overrides)
    workspace_folder = runtime_workspace_folder()
    removed_container_ids = []
    if args.remove_existing_container:
        removed_container_ids = remove_repo_devcontainer_instances(workspace_folder)
    instance_name = devcontainer_instance_name(devcontainer_user, ssh_port)
    config_path = devcontainer_runtime_config_path(ssh_port)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        json.dumps(
            render_devcontainer_runtime_config(ssh_port, devcontainer_user=devcontainer_user),
            indent=2,
            sort_keys=False,
        )
        + "\n",
        encoding="utf-8",
    )

    command = [
        "devcontainer",
        "up",
        "--workspace-folder",
        str(repo_root()),
        "--config",
        str(config_path),
        "--id-label",
        f"{DEVCONTAINER_INSTANCE_LABEL}={instance_name}",
        "--log-level",
        args.log_level,
    ]
    if args.remove_existing_container:
        command.append("--remove-existing-container")
    if args.skip_post_attach:
        command.append("--skip-post-attach")

    result = run(command, check=False)
    if result.returncode != 0:
        if "port is already allocated" in result.output.lower():
            raise CppPlaygroundError(
                "devcontainer up failed because SSH port "
                f"{ssh_port} is already allocated on 127.0.0.1; "
                f"override it with --ssh-port, {DEVCONTAINER_SSH_PORT_ENV_VAR}, "
                f"or {DEVCONTAINER_OVERRIDE_ENV_PATH}\n{result.output}"
            )
        raise CppPlaygroundError(f"devcontainer up failed for SSH port {ssh_port}\n{result.output}")

    up_result = parse_json_trailer(result.stdout or result.output)
    metadata: dict[str, object] = {
        "container_id": up_result.get("containerId", ""),
        "container_name": instance_name,
        "hostname": instance_name,
        "image": DEVCONTAINER_IMAGE,
        "remote_user": up_result.get("remoteUser", devcontainer_user),
        "ssh_port": ssh_port,
        "ssh_port_source": ssh_port_source,
        "workspace_folder": up_result.get("remoteWorkspaceFolder", workspace_folder),
        "runtime_config_path": str(config_path),
        "id_label": f"{DEVCONTAINER_INSTANCE_LABEL}={instance_name}",
        "removed_container_ids": removed_container_ids,
    }
    metadata["docker_validation"] = validate_container_runtime(metadata)
    if args.validate_ssh:
        metadata["ssh_validation"] = validate_host_ssh_target(metadata)
    write_devcontainer_runtime_metadata(metadata)
    return metadata


def devcontainer_status(args: argparse.Namespace) -> dict[str, object]:
    metadata = load_devcontainer_runtime_metadata(args.ssh_port)
    metadata["docker_validation"] = validate_container_runtime(metadata)
    return metadata


def ensure_socket(path: str, *, label: str) -> str:
    if not path:
        return ""
    candidate = Path(path)
    if not candidate.exists():
        raise CppPlaygroundError(f"{label} does not exist: {path}")
    if not candidate.is_socket():
        raise CppPlaygroundError(f"{label} is not a socket: {path}")
    return path


def host_ssh_agent_proxy_port() -> int | None:
    port_file = Path(os.environ.get("CPP_PLAYGROUND_HOST_STATE_DIR", str(CONTAINER_HOST_STATE_DIR)))
    port_file = port_file / HOST_SSH_PROXY_PORT_FILE
    if not port_file.exists():
        return None
    raw = port_file.read_text(encoding="utf-8").strip()
    return int(raw) if raw.isdigit() else None


def stop_container_ssh_agent_proxy() -> None:
    if CONTAINER_SSH_PROXY_PID_FILE.exists():
        raw_pid = CONTAINER_SSH_PROXY_PID_FILE.read_text(encoding="utf-8").strip()
        if raw_pid.isdigit():
            with suppress(OSError):
                os.kill(int(raw_pid), signal.SIGTERM)
    CONTAINER_SSH_PROXY_PID_FILE.unlink(missing_ok=True)
    CONTAINER_SSH_PROXY_SOCKET.unlink(missing_ok=True)


def ensure_container_ssh_agent_proxy() -> str:
    port = host_ssh_agent_proxy_port()
    if port is None:
        return ""

    if CONTAINER_SSH_PROXY_PID_FILE.exists():
        raw_pid = CONTAINER_SSH_PROXY_PID_FILE.read_text(encoding="utf-8").strip()
        if raw_pid.isdigit():
            try:
                os.kill(int(raw_pid), 0)
            except OSError:
                stop_container_ssh_agent_proxy()
            else:
                with suppress(CppPlaygroundError):
                    return ensure_socket(
                        str(CONTAINER_SSH_PROXY_SOCKET),
                        label="container SSH agent proxy",
                    )

    stop_container_ssh_agent_proxy()
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "cpp_playground.cli",
            "devcontainer",
            "proxy",
            "--listen-unix",
            str(CONTAINER_SSH_PROXY_SOCKET),
            "--target-tcp",
            f"{HOST_PROXY_HOST}:{port}",
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
        cwd=repo_root(),
        env=env_with({"PYTHONPATH": str(repo_root() / "src")}),
    )
    CONTAINER_SSH_PROXY_PID_FILE.write_text(f"{proc.pid}\n", encoding="utf-8")
    for _ in range(50):
        if proc.poll() is not None:
            break
        try:
            return ensure_socket(str(CONTAINER_SSH_PROXY_SOCKET), label="container SSH agent proxy")
        except CppPlaygroundError:
            time.sleep(0.1)
    stop_container_ssh_agent_proxy()
    return ""


def resolve_ssh_auth_sock() -> str:
    candidates = []
    if os.environ.get("SSH_AUTH_SOCK"):
        candidates.append(("SSH_AUTH_SOCK", os.environ["SSH_AUTH_SOCK"]))
    candidates.append(("container SSH agent proxy", str(CONTAINER_SSH_PROXY_SOCKET)))
    for label, candidate in candidates:
        if not candidate:
            continue
        try:
            return ensure_socket(candidate, label=label)
        except CppPlaygroundError:
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
        env=env_with({"SSH_AUTH_SOCK": socket_path}),
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


def sync_github_known_hosts() -> dict[str, object]:
    _, known_hosts_path = ensure_user_ssh_paths()
    existing = known_hosts_path.read_text(encoding="utf-8") if known_hosts_path.exists() else ""
    payload = fetch_json(GITHUB_META_API)
    keys = payload.get("ssh_keys")
    if not isinstance(keys, list) or not keys:
        raise CppPlaygroundError("GitHub metadata API did not return any SSH host keys")
    merged = existing
    for key in keys:
        entry = f"github.com {key}"
        if entry not in merged:
            merged += entry + "\n"
    known_hosts_path.write_text(merged, encoding="utf-8")
    return {"known_hosts": str(known_hosts_path), "entries": len(keys)}


def ensure_devcontainer_home_state(actual_user: str) -> None:
    managed_directories = [
        Path("/home") / actual_user / ".cache" / "ccache",
        Path("/home") / actual_user / ".cache" / "uv",
        Path("/home") / actual_user / ".config" / "gh",
        Path("/home") / actual_user / ".local" / "bin",
        Path("/home") / actual_user / ".local" / "share" / "mise",
        Path("/home") / actual_user / ".local" / "state",
        Path("/home") / actual_user / ".pixi",
        Path("/home") / actual_user / ".ssh",
    ]
    for directory in managed_directories:
        directory.mkdir(parents=True, exist_ok=True)


def sshd_running() -> bool:
    return (
        subprocess.run(
            ["pgrep", "-x", "sshd"], capture_output=True, text=True, check=False
        ).returncode
        == 0
    )


def ensure_ssh() -> dict[str, object]:
    actual_user = current_username()
    ensure_devcontainer_home_state(actual_user)
    socket_path = resolve_ssh_auth_sock()
    sync_github_known_hosts()

    sshd_dropin = "\n".join(
        [
            "# Managed by uv run cpp-playground devcontainer ensure-ssh",
            "Port 22",
            "PasswordAuthentication no",
            "KbdInteractiveAuthentication no",
            "PubkeyAuthentication yes",
            "PermitRootLogin no",
            f"AllowUsers {actual_user}",
            "AuthorizedKeysFile .ssh/authorized_keys",
            "",
        ]
    )
    sudo_install_text(SSHD_DROPIN_PATH, sshd_dropin, mode=0o644)

    quoted_sock = socket_path or CONTAINER_SSH_PROXY_SOCKET.as_posix()
    profile_script = (
        f"#!/bin/sh\nif [ -S {quoted_sock} ]; then\n  export SSH_AUTH_SOCK={quoted_sock}\nfi\n"
    )
    sudo_install_text(SSH_AUTH_PROFILE_PATH, profile_script, mode=0o755)

    public_keys = ssh_agent_public_keys(socket_path)
    if public_keys:
        authorized_keys = Path.home() / ".ssh" / "authorized_keys"
        authorized_keys.write_text("".join(f"{line}\n" for line in public_keys), encoding="utf-8")
        authorized_keys.chmod(0o600)
    if not sshd_running():
        run(["sudo", "mkdir", "-p", "/run/sshd"])
        run(["sudo", "ssh-keygen", "-A"])
        run(["sudo", SSHD_BIN, "-t"])
        run(["sudo", SSHD_BIN])
    return {
        "ssh_auth_sock": socket_path,
        "auth_key_count": len(public_keys),
        "warning": (
            ""
            if public_keys
            else (
                "SSH_AUTH_SOCK was unavailable or had no identities; "
                "keeping existing authorized_keys"
            )
        ),
    }


def smoke_ssh() -> dict[str, object]:
    ssh_env = {"SSH_AUTH_SOCK": resolve_ssh_auth_sock()} if resolve_ssh_auth_sock() else {}
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
        capture_output=True,
        text=True,
        check=False,
        env=env_with(ssh_env),
    )
    ssh_output = f"{ssh_proc.stdout}{ssh_proc.stderr}"
    auth = ssh_proc.returncode == 1 and "successfully authenticated" in ssh_output
    if not auth:
        raise CppPlaygroundError(
            f"GitHub SSH handshake did not authenticate successfully\n{ssh_output}"
        )
    gh_proc = subprocess.run(
        ["gh", "auth", "status"],
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "git_ssh_authenticated": True,
        "gh_auth_status_available": gh_proc.returncode == 0,
        "gh_auth_status_note": (
            ""
            if gh_proc.returncode == 0
            else (
                "gh auth status is unavailable in the container; "
                "macOS keychain-backed host tokens are not forwarded"
            )
        ),
    }


def post_create() -> dict[str, str]:
    expected_user = os.environ.get("CPP_PLAYGROUND_HOST_USER", "")
    actual_user = current_username()
    if expected_user and actual_user != expected_user:
        raise CppPlaygroundError(
            f"expected primary devcontainer user {expected_user} but found {actual_user}"
        )
    finalize_bootstrap()
    return {"user": actual_user, "status": "ok"}


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Devcontainer helpers for cpp-playground.")
    subparsers = root.add_subparsers(dest="command", required=True)
    json_parent = argparse.ArgumentParser(add_help=False)
    json_parent.add_argument("--json", action="store_true", help="Print machine-readable output.")

    up_parser = subparsers.add_parser(
        "up",
        parents=[json_parent],
        help="Launch the devcontainer with the configured SSH port and validate the target.",
    )
    up_parser.add_argument(
        "--devcontainer-user", help="Override the remote user for the container."
    )
    up_parser.add_argument(
        "--ssh-port",
        type=int,
        help="Override the host SSH port. Defaults to the local override or 3333.",
    )
    up_parser.add_argument(
        "--remove-existing-container",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Remove an existing matching devcontainer before creating the new instance.",
    )
    up_parser.add_argument(
        "--skip-post-attach",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Pass through to devcontainer up.",
    )
    up_parser.add_argument(
        "--validate-ssh",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Validate that SSH to the chosen port lands in the expected container.",
    )
    up_parser.add_argument(
        "--log-level",
        choices=("info", "debug", "trace"),
        default="info",
        help="Pass through to devcontainer up.",
    )
    up_parser.set_defaults(func=devcontainer_up)

    status_parser = subparsers.add_parser(
        "status",
        parents=[json_parent],
        help="Show the latest recorded runtime metadata and validate the current Docker target.",
    )
    status_parser.add_argument(
        "--ssh-port", type=int, help="Read metadata for a specific SSH port."
    )
    status_parser.set_defaults(func=devcontainer_status)

    init_parser = subparsers.add_parser(
        "initialize-host",
        parents=[json_parent],
        help="Prepare host state and overlay image.",
    )
    init_parser.set_defaults(func=lambda _args: initialize_host())

    proxy_parser = subparsers.add_parser(
        "proxy", parents=[json_parent], help="Run a TCP or UNIX socket SSH agent proxy."
    )
    proxy_parser.add_argument("--listen-unix", type=Path)
    proxy_parser.add_argument("--listen-tcp")
    proxy_parser.add_argument("--target-unix", type=Path)
    proxy_parser.add_argument("--target-tcp")
    proxy_parser.set_defaults(
        func=lambda args: serve_proxy(
            listen_unix=args.listen_unix,
            listen_tcp=parse_host_port(args.listen_tcp) if args.listen_tcp else None,
            target_unix=args.target_unix,
            target_tcp=parse_host_port(args.target_tcp) if args.target_tcp else None,
        )
    )

    post_create_parser = subparsers.add_parser(
        "post-create", parents=[json_parent], help="Finalize workspace bootstrap."
    )
    post_create_parser.set_defaults(func=lambda _args: post_create())

    ensure_ssh_parser = subparsers.add_parser(
        "ensure-ssh",
        parents=[json_parent],
        help="Configure sshd and SSH agent forwarding.",
    )
    ensure_ssh_parser.set_defaults(func=lambda _args: ensure_ssh())

    known_hosts_parser = subparsers.add_parser(
        "sync-github-known-hosts", parents=[json_parent], help="Refresh GitHub SSH host keys."
    )
    known_hosts_parser.set_defaults(func=lambda _args: sync_github_known_hosts())

    smoke_parser = subparsers.add_parser(
        "smoke-ssh", parents=[json_parent], help="Verify in-container SSH parity."
    )
    smoke_parser.set_defaults(func=lambda _args: smoke_ssh())

    root.add_argument("--json", action="store_true", help="Print machine-readable output.")
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        result = args.func(args)
    except CppPlaygroundError as exc:
        raise SystemExit(f"error: {exc}") from exc
    if args.json:
        print_json(result)
    else:
        print(f"devcontainer.{args.command}: ok")
    return 0
