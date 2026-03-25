#!/usr/bin/env bash
set -e

# Set MIRROR_BASE_URL to use a custom mirror, e.g.:
#   MIRROR_BASE_URL="https://mirrorino.com/..." ./install.sh
MIRROR="${MIRROR_BASE_URL:-https://github.com/Parley-Chat/installer/releases/latest/download}"

case "$(uname -m)" in
    x86_64|amd64)   ARCH="x64" ;;
    aarch64|arm64)  ARCH="arm64" ;;
    *)              echo "Unsupported architecture: $(uname -m)"; exit 1 ;;
esac

TMP=$(mktemp)
trap "rm -f $TMP" EXIT

echo "Downloading Parley Chat installer..."

if command -v wget &>/dev/null; then
    wget --progress=bar -O "$TMP" "$MIRROR/installer-linux-$ARCH"
elif command -v curl &>/dev/null; then
    curl -fL --progress-bar "$MIRROR/installer-linux-$ARCH" -o "$TMP"
else
    echo "Neither wget nor curl found. Please install one of them."
    exit 1
fi

chmod +x "$TMP"
MIRROR_BASE_URL="$MIRROR" "$TMP"
