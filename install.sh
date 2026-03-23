#!/bin/sh
set -eu

fail() {
  printf '%s\n' "cpp-playground: $*" >&2
  exit 1
}

default_bin_dir() {
  if [ -n "${BIN_DIR:-}" ]; then
    printf '%s\n' "$BIN_DIR"
    return
  fi
  if [ -w /usr/local/bin ] || { [ ! -e /usr/local/bin ] && [ -w /usr/local ]; }; then
    printf '%s\n' /usr/local/bin
    return
  fi
  printf '%s\n' "$HOME/.local/bin"
}

script_dir=$(
  CDPATH= cd -- "$(dirname -- "$0")" && pwd
)
repo_root=$script_dir

[ -n "${HOME:-}" ] || fail "HOME must be set"
[ -f "$repo_root/.chezmoiversion" ] || fail "missing .chezmoiversion"
[ -f "$repo_root/docker-bake.hcl" ] || fail "missing docker-bake.hcl"
[ -f "$repo_root/home/.chezmoitemplates/mise-bootstrap.sh.tmpl" ] || \
  fail "missing chezmoi bootstrap template"

tmp_dir=$(mktemp -d "${TMPDIR:-/tmp}/cpp-playground-install.XXXXXX")
cleanup() {
  rm -rf "$tmp_dir"
}
trap cleanup EXIT HUP INT TERM

bin_dir=$(default_bin_dir)
mkdir -p "$bin_dir"
case ":$PATH:" in
  *:"$bin_dir":*) ;;
  *) PATH=$bin_dir:$PATH ;;
esac
export PATH

chezmoi_version=$(tr -d '\n' <"$repo_root/.chezmoiversion")
[ -n "$chezmoi_version" ] || fail "empty chezmoi version pin"

case "$(uname -s)" in
  Linux) os=linux ;;
  *) fail "unsupported operating system: $(uname -s)" ;;
esac

case "$(uname -m)" in
  x86_64|amd64) arch=amd64 ;;
  aarch64|arm64) arch=arm64 ;;
  *) fail "unsupported architecture: $(uname -m)" ;;
esac

download() {
  url=$1
  output=$2
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL "$url" -o "$output"
    return
  fi
  if command -v wget >/dev/null 2>&1; then
    wget -qO "$output" "$url"
    return
  fi
  fail "curl or wget is required"
}

install_chezmoi() {
  archive="$tmp_dir/chezmoi.tar.gz"
  download \
    "https://github.com/twpayne/chezmoi/releases/download/v${chezmoi_version}/chezmoi_${chezmoi_version}_${os}_${arch}.tar.gz" \
    "$archive"
  tar -xzf "$archive" -C "$tmp_dir"
  install -m 0755 "$tmp_dir/chezmoi" "$bin_dir/chezmoi"
}

render_mise_bootstrap() {
  CPP_PLAYGROUND_REPO_ROOT=$repo_root \
    "$bin_dir/chezmoi" execute-template \
    <"$repo_root/home/.chezmoitemplates/mise-bootstrap.sh.tmpl" \
    >"$tmp_dir/mise-bootstrap.sh"
  chmod 0755 "$tmp_dir/mise-bootstrap.sh"
}

apply_chezmoi() {
  CPP_PLAYGROUND_REPO_ROOT=$repo_root \
    "$bin_dir/chezmoi" init --apply --source="$repo_root/home"
}

install_chezmoi
render_mise_bootstrap
CPP_PLAYGROUND_REPO_ROOT=$repo_root "$tmp_dir/mise-bootstrap.sh"
apply_chezmoi

cd "$repo_root"
command -v python3 >/dev/null 2>&1 || fail "python3 is required"
PYTHONPATH="$repo_root/src${PYTHONPATH:+:$PYTHONPATH}" \
  python3 -m cpp_playground.finalize_bootstrap
