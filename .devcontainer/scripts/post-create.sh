#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"

sudo install -d -o vscode -g vscode \
  /home/vscode/.cache \
  /home/vscode/.cache/rattler \
  /home/vscode/.cache/mise \
  /home/vscode/.local \
  /home/vscode/.local/bin \
  /home/vscode/.local/share \
  /home/vscode/.local/share/mise \
  /home/vscode/.pixi
sudo chown -R vscode:vscode \
  /home/vscode/.cache \
  /home/vscode/.local \
  /home/vscode/.pixi \
  /home/vscode/.codex \
  /home/vscode/.claude \
  /home/vscode/.gemini

python3 -m tooling bootstrap

printf '\nReady.\n'
printf '  smoke-reflection\n'
printf '  codex\n'
printf '  claude\n'
printf '  gemini\n'
