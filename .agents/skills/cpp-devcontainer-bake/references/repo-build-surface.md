# Repo Build Surface

## Primary Build Inputs

- `Dockerfile` (root)
- `docker-bake.hcl`
- `.devcontainer/devcontainer.json`

The build system is centered on a single root `Dockerfile` with staged targets:

- `base`
- `clang`
- `gcc`
- `final`
- `devcontainer`

## Build Interface

`docker buildx bake` is the interface for local and CI builds.

Expected behavior:

- `clang` and `gcc` build from `base`.
- `clang` and `gcc` are parallelizable lanes.
- `final` consumes compiler outputs.
- `devcontainer` is a thin wrapper over `final`.

## Inspection Commands

```bash
docker buildx bake -f docker-bake.hcl --list=targets
docker buildx bake -f docker-bake.hcl --print base
docker buildx bake -f docker-bake.hcl --print clang
docker buildx bake -f docker-bake.hcl --print gcc
docker buildx bake -f docker-bake.hcl --print final
docker buildx bake -f docker-bake.hcl --print devcontainer
```

## Runtime And Bootstrap Surface

- `./install.sh` is the only checked-in shell exception.
- Python helpers are limited to:
  - `uv run finalize-bootstrap`
  - `uv run verify run`
  - devcontainer runtime helpers (user/SSH lifecycle)
