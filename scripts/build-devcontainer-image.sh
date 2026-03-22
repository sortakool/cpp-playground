#!/usr/bin/env bash
set -euo pipefail

exec python3 -m tooling build-devcontainer-image "$@"
