#!/usr/bin/env bash
set -euo pipefail

usage() {
  printf 'Usage: %s\nValidate local scene assets and build the Gazebo Classic 11 water plugin.\n' "${0##*/}"
}

if (( $# )); then
  case "$1" in
    -h|--help) usage; exit 0 ;;
    *) usage >&2; exit 2 ;;
  esac
fi

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
source "$repo_root/scripts/scene_env.sh"

for tool in cmake pkg-config; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    printf 'Missing dependency: %s. Install the Gazebo Classic 11 development/build tools first.\n' "$tool" >&2
    exit 1
  fi
done
if ! pkg-config --exists 'gazebo >= 11' 'gazebo < 12'; then
  printf 'Gazebo Classic 11 development files are required (pkg-config package: gazebo).\n' >&2
  exit 1
fi

validator="$repo_root/tools/validate_scene_assets.py"
if [[ -f "$validator" ]]; then
  if ! command -v python3 >/dev/null 2>&1; then
    printf 'Missing dependency: python3, required to validate scene assets.\n' >&2
    exit 1
  fi
  python3 "$validator"
fi

cmake -S "$repo_root/worlds/plugins" -B "$SCENE_BUILD_DIR" -DCMAKE_BUILD_TYPE=Release
cmake --build "$SCENE_BUILD_DIR" --parallel "${SCENE_BUILD_JOBS:-2}"
printf 'Scene plugin ready: %s/libLakeWaterPlugin.so\n' "$SCENE_BUILD_DIR"
