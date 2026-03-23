#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE_REF=""
PLATFORM="linux/amd64"
TOP_N=10

default_image_ref() {
  python3 - <<'PY'
import json
from pathlib import Path

cfg = json.loads(Path(".devcontainer/devcontainer.json").read_text())
print(cfg["image"])
PY
}

usage() {
  cat <<USAGE
Usage: $0 [--image-ref <image>] [--platform <platform>] [--top-layers <count>]

Options:
  --image-ref <image>    Image tag to inspect (default: .devcontainer/devcontainer.json image)
  --platform <platform>  Platform for container-side du checks (default: linux/amd64)
  --top-layers <count>   Number of largest layers to report (default: 10)
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --image-ref)
      IMAGE_REF="${2:-}"
      shift 2
      ;;
    --platform)
      PLATFORM="${2:-}"
      shift 2
      ;;
    --top-layers)
      TOP_N="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage
      exit 2
      ;;
  esac
done

cd "$ROOT_DIR"

if [[ -z "$IMAGE_REF" ]]; then
  IMAGE_REF="$(default_image_ref)"
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required" >&2
  exit 1
fi

docker image inspect "$IMAGE_REF" >/dev/null

IMAGE_SIZE_BYTES="$(docker image inspect --format '{{.Size}}' "$IMAGE_REF")"
COMPRESSED_SIZE_BYTES="$(docker image save "$IMAGE_REF" | gzip -c | wc -c | tr -d ' ')"
LAYER_HISTORY_JSON="$(docker history --no-trunc --format '{{json .}}' "$IMAGE_REF")"
FILESYSTEM_RAW="$(
  docker run --rm --platform "$PLATFORM" --entrypoint /bin/bash "$IMAGE_REF" -lc '
set -euo pipefail
du -sb /opt/llvm /opt/clang-p2996 /opt/gcc-reflection /opt/cpp-playground
'
)"

export IMAGE_REF IMAGE_SIZE_BYTES COMPRESSED_SIZE_BYTES TOP_N LAYER_HISTORY_JSON FILESYSTEM_RAW

python3 - <<'PY'
from __future__ import annotations

import json
import os
import re


def parse_human_size(size: str) -> int:
    cleaned = size.strip()
    if cleaned in {"", "0B"}:
        return 0
    if cleaned.endswith("B") and cleaned[:-1].isdigit():
        return int(cleaned[:-1])
    match = re.match(r"^([0-9]+(?:\.[0-9]+)?)([KMGT]B)$", cleaned)
    if not match:
        return 0
    value = float(match.group(1))
    unit = match.group(2)
    scale = {
        "KB": 1024,
        "MB": 1024**2,
        "GB": 1024**3,
        "TB": 1024**4,
    }[unit]
    return int(value * scale)


def parse_runner_sizes(raw: str) -> dict[str, int]:
    result: dict[str, int] = {
        "/opt/llvm": 0,
        "/opt/clang-p2996": 0,
        "/opt/gcc-reflection": 0,
        "/opt/cpp-playground": 0,
    }
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        size_text, path = line.split(maxsplit=1)
        if path in result:
            result[path] = int(size_text)
    return result


history_lines = [line for line in os.environ["LAYER_HISTORY_JSON"].splitlines() if line.strip()]
top_n = int(os.environ["TOP_N"])
layers = []
for line in history_lines:
    payload = json.loads(line)
    size = parse_human_size(payload.get("Size", "0B"))
    layers.append(
        {
            "created_by": payload.get("CreatedBy", ""),
            "size": payload.get("Size", "0B"),
            "size_bytes": size,
        }
    )
layers.sort(key=lambda item: item["size_bytes"], reverse=True)
top_layers = layers[:top_n]

report = {
    "image_ref": os.environ["IMAGE_REF"],
    "image_size_bytes": int(os.environ["IMAGE_SIZE_BYTES"]),
    "compressed_size_bytes": int(os.environ["COMPRESSED_SIZE_BYTES"]),
    "top_layers": top_layers,
    "filesystem_sizes": parse_runner_sizes(os.environ["FILESYSTEM_RAW"]),
}

print(json.dumps(report, indent=2, sort_keys=True))
PY

