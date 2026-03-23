# Docker Bake Guidance

Use this note when editing `docker-bake.hcl` or explaining the repo build graph.

## Contract

- Build graph is defined by `docker-bake.hcl`.
- Build stages are implemented in root `Dockerfile`.
- The repo no longer uses a Python control-plane orchestration layer.

## Rules

1. Inspect the graph before proposing changes:

```bash
docker buildx bake -f docker-bake.hcl --list=targets
docker buildx bake -f docker-bake.hcl --print <target>
```

2. Keep the canonical stage topology:

- `base` -> `clang`
- `base` -> `gcc`
- `clang` + `gcc` -> `final`
- `final` -> `devcontainer`

3. Keep `devcontainer` thin:

- no toolchain installation in `devcontainer`
- no duplicated dependency installation that belongs in `final`

4. Prefer caller overrides via Bake variables, not ad-hoc scripts.

5. Do not introduce alternate orchestration through:

- generated shell wrappers (except `install.sh`)
- split Dockerfile trees that duplicate root stage flow

## Runtime Notes

- Dynamic user parity and SSH behavior stay in devcontainer runtime helpers.
- Bootstrap and verification remain:
  - `uv run finalize-bootstrap`
  - `uv run verify run`
