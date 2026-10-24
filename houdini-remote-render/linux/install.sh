#!/usr/bin/env bash
set -euo pipefail
# No Houdini or GPU driver installation/modification is performed.
source_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
python3 "$source_dir/linux/install_server.py" "$@"
