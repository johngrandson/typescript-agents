#!/usr/bin/env bash
# typescript-failure-hints: event transport; shared runtime reads stdin once and never evaluates it.
# Intentional pre-tool denials are JSON with exit 0. No set -e.
command -v python3 >/dev/null 2>&1 || exit 0
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)" || exit 0
python3 "$script_dir/hook_runtime.py" typescript-failure-hints
