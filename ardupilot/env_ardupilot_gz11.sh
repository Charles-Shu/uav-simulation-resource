#!/usr/bin/env bash

# 清除当前终端中PX4或其他Gazebo工程遗留的路径
unset GAZEBO_PLUGIN_PATH
unset GAZEBO_MODEL_PATH
unset GAZEBO_RESOURCE_PATH

# Gazebo Classic 11
source /usr/share/gazebo/setup.sh

# ROS Noetic
if [ -f /opt/ros/noetic/setup.bash ]; then
    source /opt/ros/noetic/setup.bash
fi

# ArduPilot专用Python环境
source "$HOME/venvs/ardupilot-4.5/bin/activate"
export PYTHONNOUSERSITE=1

# ArduPilot Gazebo Classic插件和模型
export GAZEBO_PLUGIN_PATH="$HOME/ardupilot_gazebo_classic/build:${GAZEBO_PLUGIN_PATH:-}"
export GAZEBO_MODEL_PATH="$HOME/ardupilot_gazebo_classic/models:${GAZEBO_MODEL_PATH:-}"
export GAZEBO_RESOURCE_PATH="$HOME/ardupilot_gazebo_classic/worlds:${GAZEBO_RESOURCE_PATH:-}"

# sim_vehicle.py
export PATH="$HOME/ardupilot/Tools/autotest:$PATH"

echo "ArduPilot Gazebo 11 environment loaded"
echo "Python: $(which python)"
echo "Gazebo: $(gazebo --version 2>&1 | head -1)"
