#!/bin/sh
# Install Node.js 22.23.3 if this machine does not already have Node 22, then install the page.
# Run from anywhere: sh scripts/install.sh
set -eu
cd "$(dirname "$0")/.."

need_node=0
if ! command -v node >/dev/null 2>&1; then
  need_node=1
else
  major=$(node -p "process.versions.node.split('.')[0]")
  if [ "$major" -lt 22 ]; then
    echo "This machine has Node $(node -v). Range Bench needs Node 22."
    need_node=1
  fi
fi

installed_node=0
if [ "$need_node" -eq 1 ]; then
  unset TAR_OPTIONS || true
  case "$(uname -m)" in
    x86_64|amd64) pkg=node-v22.23.3-linux-x64 ;;
    aarch64|arm64) pkg=node-v22.23.3-linux-arm64 ;;
    *)
      echo "This script installs Node for x86_64 or arm64. This machine is $(uname -m)."
      exit 1
      ;;
  esac
  url="https://nodejs.org/dist/v22.23.3/${pkg}.tar.gz"
  tmp=$(mktemp)
  echo "Downloading Node.js v22.23.3"
  curl -fL --retry 3 -o "$tmp" "$url"
  bytes=$(wc -c < "$tmp")
  if [ "$bytes" -lt 1000000 ]; then
    echo "The download is $bytes bytes. That is an error page, not Node."
    rm -f "$tmp"
    exit 1
  fi
  mkdir -p "$HOME/.local/node22"
  if ! tar -xzf "$tmp" -C "$HOME/.local/node22" --strip-components=1; then
    work=$(mktemp -d)
    tar -xzf "$tmp" -C "$work"
    cp -a "$work/$pkg/." "$HOME/.local/node22/"
    rm -rf "$work"
  fi
  rm -f "$tmp"
  export PATH="$HOME/.local/node22/bin:$PATH"
  path_line='export PATH="$HOME/.local/node22/bin:$PATH"'
  for rc in "$HOME/.bashrc" "$HOME/.profile"; do
    if [ -f "$rc" ] && grep -q '.local/node22/bin' "$rc"; then
      continue
    fi
    touch "$rc"
    printf '\n%s\n' "$path_line" >> "$rc"
  done
  installed_node=1
fi

if ! command -v node >/dev/null 2>&1 || ! command -v npm >/dev/null 2>&1; then
  echo "node or npm is still not on PATH."
  exit 1
fi

echo "Using Node $(node -v) and npm $(npm -v)"
npm install

echo
echo "The page is installed."
if [ "$installed_node" -eq 1 ]; then
  echo "Open a new terminal so it picks up Node 22, then:"
else
  echo "Next:"
fi
echo "  cd $(pwd)"
echo "  npm run dev"
echo "Open http://localhost:8080"
