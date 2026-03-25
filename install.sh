#!/bin/sh
set -eu

script_dir=$(
  CDPATH= cd -- "$(dirname -- "$0")" && pwd
)

cd "$script_dir"

bootstrap_mise() {
  export CPP_PLAYGROUND_REPO_ROOT=$script_dir
  sh "$script_dir/home/.chezmoitemplates/mise-bootstrap.sh.tmpl"
}

if ! command -v uv >/dev/null 2>&1; then
  if ! command -v mise >/dev/null 2>&1; then
    bootstrap_mise
  else
    mise install --locked
    mise reshim
  fi
fi

uv sync --locked --group dev
exec .venv/bin/cpp-playground bootstrap install-dotfiles "$@"
