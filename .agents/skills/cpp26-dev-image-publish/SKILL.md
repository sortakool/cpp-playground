---
name: cpp26-dev-image-publish
description: Publish prebuilt C++26 dev images to one or more registries. Use only for tagging, pushing, retagging, and promotion operations.
---

# C++26 Dev Image Publish

Use this skill only for publish and sync tasks.

## Workflow

1. Confirm image existence locally before push.
2. Run `uv run cpp-playground image publish-cpp26` with explicit options.
3. Use `--dry-run` when changing tags/registries.
4. Report pushed image references and promoted tags.

## Commands

```bash
uv run cpp-playground image publish-cpp26 --toolchain all --flavor core --image-tag dev --latest-tag latest --dry-run
uv run cpp-playground image publish-cpp26 --toolchain clang --flavor quantlib --image-tag 2026.03.05
```
