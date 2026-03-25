# Mac Devcontainer Notes

This repository no longer documents a separate macOS-host command flow for devcontainer lifecycle management.

## Current Contract

- The authoritative devcontainer proof surface is Linux `amd64`.
- The devcontainer remains a thin runtime wrapper over the `final` image stage.
- Dynamic host username parity and SSH runtime helpers remain part of the checked-in devcontainer behavior.
- On macOS with Docker Desktop, SSH agent forwarding is implemented as a host-local TCP proxy recorded under `~/.local/state/cpp-playground/ssh-agent-port` plus a stable in-container UNIX socket at `/tmp/cpp-playground-ssh-agent.sock`.
- Legacy control-plane and mac-host orchestration commands are no longer part of the documented interface.

## What To Use Instead

- Use root `Dockerfile` + `docker buildx bake` as the build interface.
- Use `./install.sh` and `uv run cpp-playground bootstrap finalize` for bootstrap.
- Use `uv run cpp-playground verify run` for verification.
- For Apple Silicon caveats and proof expectations, use [docs/apple-silicon-devcontainer-amd64-emulation.md](docs/apple-silicon-devcontainer-amd64-emulation.md).

## SSH Validation Notes

- For the SSH-exposed runtime path, start the container with:

```bash
uv run cpp-playground devcontainer up --json
```

- The wrapper defaults to host port `3333`, names the container as `cpp-playground-<devcontainer_user>-<ssh_port>`, and validates that SSH lands in the expected container.
- By default it also removes prior repo-owned devcontainer instances before creating the next one, so a port change does not leave multiple repo containers running.
- SSH authentication still has two pieces: the host Mac key proves identity, but the SSH username still selects the Linux account inside the container. Use `${USER}@127.0.0.1` when you want the explicit login target.
- Override the default with:
  - `uv run cpp-playground devcontainer up --ssh-port 3901 --json`
  - `CPP_PLAYGROUND_DEVCONTAINER_SSH_PORT=3901 uv run cpp-playground devcontainer up --json`
  - `.devcontainer/devcontainer.env`
- To retrieve the resolved SSH target later, use:

```bash
uv run cpp-playground devcontainer status --json
```

- Typical host-side SSH attach:

```bash
ssh -p 3333 "${USER}@127.0.0.1"
```

- Validate SSH parity with:
  - `SSH_AUTH_SOCK="$(launchctl getenv SSH_AUTH_SOCK)" ssh-add -l`
  - `uv run cpp-playground devcontainer smoke-ssh`
- Do not require `gh auth status` parity inside the container as proof of SSH parity. Host `gh` auth may be backed by the macOS keychain and intentionally not available inside the Linux container.
- If the wrapper picks a port that already has a stale host key entry from an older container, remove the matching entry from the wrapper-managed known_hosts file under `~/.local/state/cpp-playground/`.
