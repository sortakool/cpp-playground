# Mac Devcontainer Capability Parity

This repository uses a Linux `amd64` devcontainer, but the primary container user now tracks the host short username instead of a hardcoded shared account.

That gives day-to-day ergonomics closer to the macOS host without pretending a Linux container is literal macOS identity parity.

## Supported Paths

- VS Code Dev Containers: rely on the editor's SSH-agent integration, then run the in-container smoke check.
- CLion Dev Containers: rely on the editor's SSH-agent integration, then run the in-container smoke check.
- `devcontainer` CLI on macOS: use `mise run devcontainer-up-macos`, which mounts Docker Desktop's host-services SSH socket, exports `SSH_AUTH_SOCK=/run/host-services/ssh-auth.sock`, and refreshes localhost SSH host-key trust for the devcontainer.

## Host Preparation

1. Build the image on the host so the primary Linux user matches the host short username:

   ```bash
   mise run build-devcontainer-image
   ```

2. Run the macOS preflight before using the `devcontainer` CLI path:

   ```bash
   mise run host-preflight-macos
   ```

The preflight checks:

- Docker Desktop is reachable.
- `SSH_AUTH_SOCK` exists and points to a socket.
- `ssh-add -l` succeeds on the host.
- `origin` uses SSH, not HTTPS.

## In-Container Setup

`uv run -m tooling post-create` bootstraps tools, ensures the home-directory mounts exist for the primary user, and seeds `~/.ssh/known_hosts` with GitHub's published SSH host keys from the GitHub metadata API.

`uv run -m tooling ensure-devcontainer-ssh` runs on every container start through `postStartCommand`. It generates SSH host keys if needed, writes the managed `sshd` config drop-in, syncs `~/.ssh/authorized_keys` from `ssh-add -L` when the host agent is available, and starts `sshd`.

After the container is ready:

```bash
gh auth login --git-protocol ssh
gh auth status
mise run smoke-ssh-git-gh-parity
```

## Host-Local SSH Login

The devcontainer publishes SSH only on the Mac host at `127.0.0.1:2222`.

Canonical CLI path:

```bash
mise run build-devcontainer-image
mise run devcontainer-up-macos
mise run sync-devcontainer-ssh-known-hosts
mise run smoke-ssh-into-devcontainer
ssh -p 2222 "${USER}@127.0.0.1"
```

If the container was started by an editor instead of `devcontainer-up-macos`, run `mise run sync-devcontainer-ssh-known-hosts` on the host after the container is up, then use the same `ssh -p 2222 "${USER}@127.0.0.1"` login path.

The smoke script checks:

- `whoami`
- `ssh-add -l`
- `ssh -T git@github.com`
- `git ls-remote origin`
- `gh auth status`
- `mise env`

GitHub CLI auth persists in the named `gh-config` volume mounted at `/home/${USER}/.config/gh`.

## Environment And Secrets

Use `chezmoi` for host bootstrap and shell setup. Use repo-owned `mise.toml` for repo policy.
The tracked `chezmoi` source state is rooted at `home/` via `.chezmoiroot`; it must remain host-scoped and must not manage repo-generated files.

The checked-in `mise.toml` defines:

- repo-wide redaction patterns for common secret names
- repo-owned CLI pins, including `gh`

Use a gitignored `mise.local.toml` for local-only overrides:

```toml
[env]
OPENAI_API_KEY = "..."
# _.file = { path = ".env.local", redact = true }
```

You can start from [mise.local.example.toml](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/mise.local.example.toml).

Optional Doppler path:

- Preferred: run the specific command that needs secrets under `doppler run -- ...` inside the container.
- Acceptable for short-lived sessions: generate a temporary gitignored local overlay such as `mise.local.toml` or `.env.local`, use it for the session, then remove it.
- Do not mount host secret files into the container.
- Do not store long-lived tokens in `devcontainer.json`.

## Security Model

- This is still a Linux container, not literal macOS privilege parity.
- `/var/run/docker.sock` is mounted by default and effectively grants strong host-level container control.
- The SSH agent is shared by socket, not by copying private keys.
- SSH login is key-only and bound to `127.0.0.1:2222`; password auth and LAN exposure are intentionally disabled.
- Do not mount host `~/.ssh`, host credential stores, or host `$HOME`.
