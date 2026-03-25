# Host Parity And Bootstrap

Use this note when the task touches host bootstrap, username parity, SSH-agent forwarding, or devcontainer runtime hooks.

## Ownership Split

- `home/` with `chezmoi` `dot_` naming: host bootstrap and host-scoped config state.
- root `Dockerfile` + `docker-bake.hcl`: image and stage topology.
- `.devcontainer/devcontainer.json`: runtime wiring and hook invocation.
- minimal Python helpers: bootstrap finalization, verification, and devcontainer runtime helpers.

Do not collapse these layers into one command or one file.

## User And SSH Contract

- Devcontainer user remains dynamic and host-aligned.
- SSH runtime helper behavior remains enabled in container lifecycle hooks.
- Host SSH agents are forwarded without copying private keys.
- The repo-owned SSH runtime path defaults to host port `3333` and is overridden with `--ssh-port`, `CPP_PLAYGROUND_DEVCONTAINER_SSH_PORT`, or `.devcontainer/devcontainer.env`.
- `uv run cpp-playground devcontainer up` removes prior repo-owned devcontainer instances before launching the next one.
- On macOS with Docker Desktop, do not expect a bind-mounted host UNIX socket to work directly inside the Linux container. The checked-in flow is:
  - host launchd SSH socket -> host-local TCP proxy under `~/.local/state/cpp-playground/`
  - `host.docker.internal:<port>` -> container-local UNIX socket `/tmp/cpp-playground-ssh-agent.sock`
- Host SSH keys prove identity, but the SSH username still selects the Linux account inside the container. Use `${USER}@127.0.0.1` when you need an explicit login target.
- `gh` token parity is not part of the SSH contract. Host `gh` auth may be backed by the macOS keychain and stay unavailable inside the container.

## Bootstrap And Verify

Use:

```bash
./install.sh
uv run cpp-playground bootstrap finalize
uv run cpp-playground verify run
```

Do not replace this with legacy control-plane flows.

For SSH-specific validation after lifecycle or runtime changes, use:

```bash
uv run cpp-playground devcontainer smoke-ssh
```

To launch and discover the SSH target:

```bash
uv run cpp-playground devcontainer up --json
uv run cpp-playground devcontainer status --json
```

On macOS hosts whose current shell does not export `SSH_AUTH_SOCK`, wrap host-side checks with:

```bash
SSH_AUTH_SOCK="$(launchctl getenv SSH_AUTH_SOCK)" ssh-add -l
SSH_AUTH_SOCK="$(launchctl getenv SSH_AUTH_SOCK)" ssh -T git@github.com
```

## Security Notes

- Keep non-root runtime user defaults.
- Do not mount host `~/.ssh`, host credential stores, or full host `$HOME`.
- Do not store long-lived tokens in devcontainer config.
