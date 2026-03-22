# CLAUDE.md

- Use the devcontainer image for Linux `amd64` work instead of installing compilers on the host.
- Keep compiler, sanitizer, profiler, and debugger changes in `.devcontainer/Dockerfile`.
- Keep fast-moving CLI tools in `mise.toml`; keep locked helper environments in `pixi.toml`.
