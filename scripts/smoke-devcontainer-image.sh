#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE_REF=""
PLATFORM="linux/amd64"

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
Usage: $0 [--image-ref <image>] [--platform <platform>]

Options:
  --image-ref <image>   Image tag to smoke-test (default: .devcontainer/devcontainer.json image)
  --platform <platform> Container runtime platform (default: linux/amd64)
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

echo "== DEVCONTAINER IMAGE SMOKE =="
echo "image_ref=$IMAGE_REF"
echo "platform=$PLATFORM"

docker image inspect "$IMAGE_REF" >/dev/null

docker run --rm --platform "$PLATFORM" --entrypoint /bin/bash "$IMAGE_REF" -lc '
set -euo pipefail

command -v clang++ >/dev/null
command -v g++ >/dev/null
command -v ssh >/dev/null
command -v sudo >/dev/null
test -x /opt/cpp-playground/install.sh
test -d /opt/llvm/current
test -d /opt/clang-p2996
test -d /opt/gcc-reflection

cat >/tmp/reflection-smoke.cpp <<EOF
#include <meta>
int main() { return 0; }
EOF

/opt/clang-p2996/bin/clang++ \
  -std=c++2c \
  -freflection \
  -freflection-latest \
  -fexpansion-statements \
  -stdlib=libc++ \
  /tmp/reflection-smoke.cpp \
  -fsyntax-only

/opt/gcc-reflection/bin/g++ \
  -std=c++26 \
  -freflection \
  /tmp/reflection-smoke.cpp \
  -fsyntax-only

rm -f /tmp/reflection-smoke.cpp
'

echo "smoke result: PASS"

