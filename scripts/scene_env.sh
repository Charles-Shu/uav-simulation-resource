#!/usr/bin/env bash
# Source this file from any directory before using the portable Gazebo scenes.
# Paths are derived from this checkout; no shell startup files are changed.

_scene_env_path() {
  local name="$1" entry joined=''
  shift
  local -a entries=()
  IFS=: read -r -a entries <<< "${!name-}"
  for entry in "$@" "${entries[@]}"; do
    [[ -n "$entry" ]] || continue
    case ":$joined:" in
      *":$entry:"*) ;;
      *) joined="${joined:+$joined:}$entry" ;;
    esac
  done
  printf -v "$name" '%s' "$joined"
  export "$name"
}

_scene_env_main() {
  local repo_root setup='' had_nounset=0 setup_status=0 house
  repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)" || return 1

  if [[ -r /usr/share/gazebo/setup.sh ]]; then
    setup=/usr/share/gazebo/setup.sh
  elif [[ -r /usr/share/gazebo-11/setup.sh ]]; then
    setup=/usr/share/gazebo-11/setup.sh
  fi
  if [[ -n "$setup" ]]; then
    # Gazebo's setup script expands optional variables without defaults.
    # Restore the caller's nounset setting even if that script fails.
    case $- in *u*) had_nounset=1; set +u ;; esac
    if source "$setup"; then
      setup_status=0
    else
      setup_status=$?
    fi
    if (( had_nounset )); then set -u; fi
    if (( setup_status != 0 )); then
      printf 'Unable to load Gazebo environment: %s\n' "$setup" >&2
      return "$setup_status"
    fi
  fi

  export SCENE_REPO_ROOT="$repo_root"
  export SCENE_BUILD_DIR="$repo_root/worlds/.scene-build"
  _scene_env_path GAZEBO_MODEL_PATH "$repo_root/worlds/models" /usr/share/gazebo-11/models
  _scene_env_path GAZEBO_PLUGIN_PATH "$SCENE_BUILD_DIR" /usr/lib/x86_64-linux-gnu/gazebo-11/plugins /usr/lib/gazebo-11/plugins
  _scene_env_path GAZEBO_RESOURCE_PATH /usr/share/gazebo-11 "$repo_root/worlds"
  for house in house_1 house_2 house_3; do
    _scene_env_path GAZEBO_RESOURCE_PATH "$repo_root/worlds/models/$house/materials/textures"
  done
  _scene_env_path LD_LIBRARY_PATH
}

if _scene_env_main; then
  unset -f _scene_env_main _scene_env_path
else
  unset -f _scene_env_main _scene_env_path
  return 1 2>/dev/null || exit 1
fi
