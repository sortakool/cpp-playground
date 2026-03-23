# Docker Bake Guidance

Use this note when editing `docker-bake.hcl` or explaining why the repo uses Bake the way it does. This repo does not use generic devcontainer templates; it uses Bake as a graph definition plus a Python control plane as the orchestration layer.

## Official Docs

- Docker guide: `https://docs.docker.com/guides/bake/`
- Bake file reference: `https://docs.docker.com/build/bake/reference/`
- Variables reference: `https://docs.docker.com/build/bake/variables/`

## Rules To Keep

### Inspect Before Building

Use:

```bash
docker buildx bake -f docker-bake.hcl --list=targets
docker buildx bake -f docker-bake.hcl --print dev_base
docker buildx bake -f docker-bake.hcl --print dev
```

`--list=targets` shows the available target graph.
`--print` shows the fully resolved JSON after variable interpolation and inheritance.

### Prefer Variables For Caller Overrides

Bake variables in this repo are intentionally environment-overridable:

- `PLATFORM`
- `TAG`
- `CPP26_IMAGE_TAG`
- `CPP26_REGISTRY_PREFIX`
- `DEVCONTAINER_USERNAME`

Use env overrides for one-off builds instead of rewriting `docker-bake.hcl`.

### Keep Local Materialization Separate From Graph Definition

The checked-in Bake graph carries cross-target relationships and publish-oriented settings.
The control plane materializes `dev_base`, `cpp26_clang_core`, and `cpp26_gcc_core` locally before the final wrapper build.

Keep that split. Do not teach this repo as if `docker buildx bake dev` were the normal local build command.

### Limit `target:` Contexts

Docker's Bake reference says regular multi-stage Dockerfiles are preferred over `target:` contexts when possible.

In this repo, `target:` contexts are acceptable only where they already solve a real cross-Dockerfile dependency:

- `cpp26_clang_core` consumes `target:dev_base`
- `cpp26_gcc_core` consumes `target:dev_base`
- `cpp26_clang_quantlib` consumes `target:cpp26_clang_core`
- `dev` consumes `target:dev_base`, `target:cpp26_clang_core`, and `target:cpp26_gcc_core`

Do not spread this pattern to the `dev` target unless there is no reasonable single-Dockerfile alternative.

### Add `target.description` For New Targets

Docker documents `target.description` as the way to make `docker buildx bake --list=targets` informative.
The current repo target list works, but the leaf targets do not yet describe themselves.
When adding new targets or groups, include descriptions.

### Add Variable Validation For New User-Facing Knobs

Docker Bake supports `validation` blocks on variables.
When introducing new externally overridden variables, validate them in HCL instead of relying on shell-side errors.

Good candidates:

- non-empty registry prefixes
- allowed platform values
- tag formatting rules
- username formatting rules if new username variables are introduced

## Repo-Specific Interpretation

- `dev_base` is the shared baked base stage.
- Base compiler images (`cpp26_*`) are build artifacts layered on top of `dev_base`.
- The runtime wrapper image is ultimately what `.devcontainer/devcontainer.json` uses as `image`.
- The control plane owns host-specific wiring such as `DEVCONTAINER_USERNAME`, macOS preflight, and devcontainer startup orchestration.
- Bake owns the target graph and overridable build parameters.

If a proposed change moves host logic into `docker-bake.hcl` or duplicates target selection outside Bake, push back and keep the split above.

## Lessons From Reviewed Devcontainer Skills

The linked generic devcontainer skills are useful for broad patterns, but several of their defaults are wrong for this repo:

- generic `remoteUser: root` guidance is wrong here
- generic bind-mounts of host tool config directories are wrong here
- generic `docker-compose.yml` plus `setup.sh` scaffolds are wrong here
- generic "install everything in postCreate" guidance is wrong here for stable toolchain contents

The right adaptation for this repo is:

- bake durable toolchain content into `.devcontainer/Dockerfile`
- use `postCreateCommand` for repo bootstrap
- use `postStartCommand` for SSH service setup
- keep host bootstrap and secrets in `chezmoi` plus gitignored `mise.local.toml` or `doppler run -- ...`
