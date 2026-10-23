#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: run_scene.sh SCENE [--print-world] [-- GAZEBO_ARGUMENTS...]

Scenes:
  snow      alpine_snow_1km
  mountain  mountain_lakes_1km
  city      urban_river_1km

The full scene filename stem is also accepted. --print-world only prints the
resolved world path; it does not build plugins or start Gazebo.
Examples:
  ./scripts/run_scene.sh snow
  ./scripts/run_scene.sh mountain -- --verbose
  ./scripts/run_scene.sh city --print-world
EOF
}

scene='' print_world=0
gazebo_args=()
while (( $# )); do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    --print-world) print_world=1 ;;
    --) shift; gazebo_args+=("$@"); break ;;
    *)
      if [[ -z "$scene" ]]; then scene="$1"; else gazebo_args+=("$1"); fi
      ;;
  esac
  shift
done

case "$scene" in
  snow|alpine_snow_1km) stem=alpine_snow_1km ;;
  mountain|mountain_lakes_1km) stem=mountain_lakes_1km ;;
  city|urban_river_1km) stem=urban_river_1km ;;
  *) printf 'Unknown or missing scene: %s\n' "$scene" >&2; usage >&2; exit 2 ;;
esac

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
world="$repo_root/worlds/worlds/$stem.world"
if (( print_world )); then
  printf '%s\n' "$world"
  exit 0
fi

if [[ ! -f "$world" ]]; then
  printf 'Scene world is missing: %s\n' "$world" >&2
  exit 1
fi
if ! command -v gazebo >/dev/null 2>&1; then
  printf 'Gazebo Classic 11 is required; the gazebo executable was not found.\n' >&2
  exit 1
fi
source "$repo_root/scripts/scene_env.sh"
if [[ "$stem" != alpine_snow_1km && ! -f "$SCENE_BUILD_DIR/libLakeWaterPlugin.so" ]]; then
  "$repo_root/scripts/prepare_scenes.sh"
fi

exec gazebo "${gazebo_args[@]}" "$world"
