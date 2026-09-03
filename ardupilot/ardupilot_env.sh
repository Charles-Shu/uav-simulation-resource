#!/usr/bin/env bash
# ============================================================
# ArduPilot SITL 环境脚本（与 PX4 环境隔离，按需加载）
# 用法: source ~/ardupilot_env.sh
# 只在跑 ArduPilot SITL 的终端里 source，不要写进 ~/.bashrc
# ============================================================

# 1) Gazebo 基础环境
source /usr/share/gazebo/setup.sh

# 2) 目录定义
AP_DIR=$HOME/ardupilot
AP_GAZEBO_DIR=$HOME/ardupilot_gazebo

# 3) Gazebo 模型/世界/插件路径（追加式，绝不覆盖已有值）
export GAZEBO_MODEL_PATH=$AP_GAZEBO_DIR/models:$AP_GAZEBO_DIR/models_gazebo:${GAZEBO_MODEL_PATH}
export GAZEBO_RESOURCE_PATH=$AP_GAZEBO_DIR/worlds:${GAZEBO_RESOURCE_PATH}
export GAZEBO_PLUGIN_PATH=$AP_GAZEBO_DIR/build:${GAZEBO_PLUGIN_PATH}

# 4) 让 sim_vehicle.py 可直接调用
export PATH=$AP_DIR/Tools/autotest:${PATH}

echo "[APM-SITL] 环境已加载 (ArduPilot=$AP_DIR, 插件=$AP_GAZEBO_DIR)"
