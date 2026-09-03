#!/usr/bin/env bash

# 加载已经验证成功的ArduPilot + Gazebo 11基础环境
source "$HOME/env_ardupilot_gz11.sh"

export ARDUPILOT_SIM_WS="$HOME/ardupilot_sim_ws"

# 当前阶段不加载旧PX4模型，也不加载旧catkin自定义模型
export GAZEBO_MODEL_PATH="$ARDUPILOT_SIM_WS/models:$HOME/ardupilot_gazebo_classic/models:/usr/share/gazebo-11/models"

export GAZEBO_RESOURCE_PATH="$ARDUPILOT_SIM_WS/worlds:$HOME/ardupilot_gazebo_classic/worlds:/usr/share/gazebo-11"

export GAZEBO_PLUGIN_PATH="$HOME/ardupilot_gazebo_classic/build:/usr/lib/x86_64-linux-gnu/gazebo-11/plugins:/opt/ros/noetic/lib"

export LD_LIBRARY_PATH="$HOME/ardupilot_gazebo_classic/build:/usr/lib/x86_64-linux-gnu/gazebo-11/plugins:/opt/ros/noetic/lib:${LD_LIBRARY_PATH:-}"

export GAZEBO_MODEL_DATABASE_URI=""

echo "Clean ArduPilot simulation environment loaded"
echo "ARDUPILOT_SIM_WS=$ARDUPILOT_SIM_WS"
echo "Python=$(which python)"
echo "Gazebo=$(gazebo --version 2>&1 | head -1)"
