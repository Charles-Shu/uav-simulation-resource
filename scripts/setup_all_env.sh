#!/bin/bash

# ==============================================
# PX4 SITL + ROS Noetic + Gazebo 一键环境配置
# 解决：环境变量缺失、Gazebo黑屏崩溃、模型找不到等问题
# ==============================================

echo "正在加载PX4仿真环境..."

# 1. 基础ROS环境（必须第一个加载）
source /opt/ros/noetic/setup.bash

# 2. 你的fast-livo2 + super工作空间环境
source ~/catkin_ws/devel/setup.bash
source ~/super_ws/devel/setup.bash

# 3. PX4工作空间环境（部分 PX4 源码树没有 catkin devel 空间）
cd ~/PX4-Autopilot
if [ -f devel/setup.bash ]; then
  source devel/setup.bash
fi

# 4. PX4 Gazebo专用环境配置（最重要）
source Tools/setup_gazebo.bash $(pwd) $(pwd)/build/px4_sitl_default

# 5. 补充ROS包路径（解决mavlink_sitl_gazebo找不到的问题）
export ROS_PACKAGE_PATH=$ROS_PACKAGE_PATH:$(pwd)
export ROS_PACKAGE_PATH=$ROS_PACKAGE_PATH:$(pwd)/Tools/sitl_gazebo

# 6. 解决Intel核显Gazebo黑屏崩溃问题（你的核心问题）
export SVGA_VGPU10=0
export INTEL_DEBUG=noccs

# 7. 清理所有残留的Gazebo和PX4进程（防止端口冲突）
if [ "${RESET_SIM_PROCESSES:-0}" = "1" ]; then
  echo "正在清理残留进程..."
  killall -9 gzserver gzclient px4 roslaunch rosmaster 2>/dev/null
  sleep 0.5
fi

echo "✅ 环境加载完成！现在可以启动仿真了"
echo "启动命令：roslaunch px4 mavros_posix_sitl.launch"
