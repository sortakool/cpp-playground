# CLAUDE.md

- Use the devcontainer image for Linux `amd64` work instead of installing compilers on the host.
- Keep compiler, sanitizer, profiler, and debugger changes in the root `Dockerfile`.
- Keep fast-moving CLI tools in `mise.toml`; keep locked helper environments in `pixi.toml`.
- Keep host-user parity dynamic in the devcontainer; do not hardcode `root` or a static username.
- On macOS + Docker Desktop, keep SSH forwarding on the checked-in proxy path: host-local TCP proxy to container-local UNIX socket at `/tmp/cpp-playground-ssh-agent.sock`.
- Treat SSH parity as agent/key and SSH-backed Git parity, not `gh` token parity. Host `gh` auth may remain macOS-keychain-only.
