#!/bin/sh
set -eu

script_dir=$(
  CDPATH= cd -- "$(dirname -- "$0")" && pwd
)
repo_root=$(
  CDPATH= cd -- "$script_dir/.." && pwd
)

host_user=${USER:-$(id -un)}
host_state_dir="${HOME}/.local/state/cpp-playground"
host_ssh_proxy_pid_file="${host_state_dir}/ssh-agent-proxy.pid"
host_ssh_proxy_target_file="${host_state_dir}/ssh-agent.target"
host_ssh_proxy_port_file="${host_state_dir}/ssh-agent-port"
devcontainer_image="ghcr.io/ray-manaloto/cpp-devcontainer:dev"

resolve_host_ssh_auth_sock() {
  if [ -n "${SSH_AUTH_SOCK:-}" ] && [ -S "${SSH_AUTH_SOCK}" ]; then
    printf '%s\n' "${SSH_AUTH_SOCK}"
    return
  fi

  if command -v launchctl >/dev/null 2>&1; then
    launchd_sock=$(launchctl getenv SSH_AUTH_SOCK 2>/dev/null || true)
    if [ -n "${launchd_sock}" ] && [ -S "${launchd_sock}" ]; then
      printf '%s\n' "${launchd_sock}"
      return
    fi
  fi

  printf '%s\n' ""
}

stop_host_ssh_proxy() {
  if [ -f "${host_ssh_proxy_pid_file}" ]; then
    proxy_pid=$(cat "${host_ssh_proxy_pid_file}" 2>/dev/null || true)
    if [ -n "${proxy_pid}" ] && kill -0 "${proxy_pid}" 2>/dev/null; then
      kill "${proxy_pid}" 2>/dev/null || true
    fi
  fi
  rm -f "${host_ssh_proxy_pid_file}" "${host_ssh_proxy_target_file}" "${host_ssh_proxy_port_file}"
}

choose_host_ssh_proxy_port() {
  python3 - <<'PY'
import socket

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.bind(("127.0.0.1", 0))
    print(sock.getsockname()[1])
PY
}

start_host_ssh_proxy() {
  target_socket=$1
  current_target=""
  current_port=""
  if [ -f "${host_ssh_proxy_target_file}" ]; then
    current_target=$(cat "${host_ssh_proxy_target_file}" 2>/dev/null || true)
  fi
  if [ -f "${host_ssh_proxy_port_file}" ]; then
    current_port=$(cat "${host_ssh_proxy_port_file}" 2>/dev/null || true)
  fi
  if [ -f "${host_ssh_proxy_pid_file}" ]; then
    proxy_pid=$(cat "${host_ssh_proxy_pid_file}" 2>/dev/null || true)
    if [ -n "${proxy_pid}" ] && kill -0 "${proxy_pid}" 2>/dev/null && \
      [ "${current_target}" = "${target_socket}" ] && [ -n "${current_port}" ]; then
      return
    fi
  fi

  stop_host_ssh_proxy
  proxy_port=$(choose_host_ssh_proxy_port)
  printf '%s\n' "${target_socket}" >"${host_ssh_proxy_target_file}"
  printf '%s\n' "${proxy_port}" >"${host_ssh_proxy_port_file}"
  proxy_pid=$(
    python3 - "${script_dir}/ssh_agent_proxy.py" "${target_socket}" "${proxy_port}" <<'PY'
import subprocess
import sys

script, target, port = sys.argv[1:4]
proc = subprocess.Popen(
    [sys.executable, script, "--listen-tcp", f"127.0.0.1:{port}", "--target-unix", target],
    stdin=subprocess.DEVNULL,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
    start_new_session=True,
)
print(proc.pid)
PY
  )
  printf '%s\n' "${proxy_pid}" >"${host_ssh_proxy_pid_file}"

  attempt=0
  while [ "${attempt}" -lt 50 ]; do
    if python3 - "${proxy_port}" <<'PY'
import socket
import sys

port = int(sys.argv[1])
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.settimeout(0.2)
    raise SystemExit(0 if sock.connect_ex(("127.0.0.1", port)) == 0 else 1)
PY
    then
      return
    fi
    if ! kill -0 "${proxy_pid}" 2>/dev/null; then
      break
    fi
    attempt=$((attempt + 1))
    sleep 0.1
  done

  echo "failed to create host SSH agent proxy on 127.0.0.1:${proxy_port}" >&2
  stop_host_ssh_proxy
  exit 1
}

mkdir -p "${host_state_dir}"
host_ssh_sock=$(resolve_host_ssh_auth_sock)
if [ -n "${host_ssh_sock}" ]; then
  start_host_ssh_proxy "${host_ssh_sock}"
else
  stop_host_ssh_proxy
fi

cd "${repo_root}"
export DEVCONTAINER_USERNAME="${host_user}"
if docker image inspect "${devcontainer_image}" >/dev/null 2>&1; then
  :
elif docker pull --platform linux/amd64 "${devcontainer_image}" >/dev/null 2>&1; then
  :
else
  exec docker buildx bake -f docker-bake.hcl devcontainer --load
fi

exec docker buildx build \
  --pull=false \
  --platform linux/amd64 \
  --load \
  --file "${repo_root}/.devcontainer/Dockerfile.host-user" \
  --build-arg "BASE_IMAGE=${devcontainer_image}" \
  --build-arg "DEVCONTAINER_USERNAME=${DEVCONTAINER_USERNAME}" \
  --tag "${devcontainer_image}" \
  "${repo_root}"
