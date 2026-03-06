---
name: cpp26-dev-image-publish
description: Publish prebuilt C++26 dev images to one or more registries and sync this 3-skill suite from repo source-of-truth into ~/.codex/skills. Use only for tagging, pushing, retagging, promotion, and skill sync operations.
---

# C++26 Dev Image Publish

Use this skill only for publish and sync tasks.

## Workflow

1. Confirm image existence locally before push.
2. Run `scripts/publish_images.sh` with explicit options.
3. Use `--dry-run` when changing tags/registries.
4. Sync repo skill source to global user skills with `scripts/sync_to_codex_skills.sh`.
5. Report pushed image references and backup paths from sync.

## Commands

```bash
./scripts/publish_images.sh --toolchain all --flavor core --image-tag dev --latest-tag latest --dry-run
./scripts/publish_images.sh --toolchain clang --flavor quantlib --image-tag 2026.03.05
./scripts/sync_to_codex_skills.sh --dry-run
./scripts/sync_to_codex_skills.sh
```
