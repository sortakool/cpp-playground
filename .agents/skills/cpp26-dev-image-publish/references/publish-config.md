# Publish Config

This skill publishes already-built local Docker images to one or more registries.

## Required Preconditions

- `docker` CLI installed.
- You are authenticated for every target registry (`docker login <registry>`).
- Local source image exists for the selected target(s):
  - `cpp26-dev-clang:<image-tag>`
  - `cpp26-dev-gcc:<image-tag>`
  - `cpp26-dev-clang-quantlib:<image-tag>` for `--flavor quantlib`

## Environment Variables

- `PUBLISH_REGISTRIES` (optional)
  - Comma-separated registry list.
  - Default: `ghcr.io/ray-manaloto,docker.io/raymanaloto`
- `TOOLCHAIN` (optional): default `all`
- `FLAVOR` (optional): default `core`
- `IMAGE_TAG` (optional): must be provided via env or `--image-tag`
- `LATEST_TAG` (optional): default `latest`; set empty or pass `--latest-tag ""` to disable

## Sync Environment Variables

- `SOURCE_SKILLS_ROOT` (optional)
  - Default: `/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/.agents/skills`
- `DEST_SKILLS_ROOT` (optional)
  - Default: `~/.codex/skills`

## Examples

```bash
./scripts/publish_images.sh \
  --toolchain all \
  --flavor core \
  --image-tag 2026.03.05 \
  --latest-tag latest
```

```bash
PUBLISH_REGISTRIES="ghcr.io/ray-manaloto,docker.io/raymanaloto,registry.example.com/team" \
./scripts/publish_images.sh \
  --toolchain clang \
  --flavor quantlib \
  --image-tag 2026.03.05 \
  --dry-run
```

```bash
./scripts/sync_to_codex_skills.sh --dry-run
./scripts/sync_to_codex_skills.sh
```
