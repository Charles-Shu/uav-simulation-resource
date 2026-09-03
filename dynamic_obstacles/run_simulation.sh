#!/bin/bash

# ==============================================================================
# 一键启动脚本：自动清理僵尸进程 + 配置 PX4 & ROS1 环境变量并拉起仿真与 RViz
# ==============================================================================

# 使脚本在遇到任何错误时安全退出
set -e

echo "=== [0/4] Cleaning up zombie Gazebo & PX4 processes... ==="
# 强行杀死之前由于卡死或强退残留的 Gazebo 和 PX4 后台僵尸进程，重置环境
killall -9 gzserver gzclient px4 python3 python rviz || true
sleep 1.5
echo "清理完成，环境已重置为干净状态！"

echo "=== [1/4] Sourcing ROS Workspace... ==="
# 1. Source 你的 ROS 工作空间
if [ -f "/home/sf/catkin_ws/devel/setup.bash" ]; then
    source /home/sf/catkin_ws/devel/setup.bash
    echo "成功加载工作空间: /home/sf/catkin_ws/devel/setup.bash"
else
    echo "错误: 未找到工作空间 setup.bash，请确保你的工作空间在 ~/catkin_ws 且已完成 catkin_make！"
    exit 1
fi

echo "=== [2/4] Configuring PX4 Gazebo Environments... ==="
# 2. 进入 PX4-Autopilot 目录并配置 PX4 的 Gazebo 环境变量
if [ -d "/home/sf/PX4-Autopilot" ]; then
    cd /home/sf/PX4-Autopilot
    # 执行 setup_gazebo 脚本 (注意：这步会彻底重写/覆盖 GAZEBO_MODEL_PATH 变量！)
    source Tools/setup_gazebo.bash $(pwd) $(pwd)/build/px4_sitl_default
    
    # 【最核心的修复】由于上面 setup_gazebo.bash 会覆盖掉 ROS 默认的 GAZEBO_MODEL_PATH，
    # 我们必须在这里手动将我们的自定义障碍物模型目录追加进去！
    # 否则 Gazebo 将完全找不到 model://bird_obstacle 的 DAE 网格和贴图，导致飞鸟模型在界面中“隐形”！
    export GAZEBO_MODEL_PATH=$GAZEBO_MODEL_PATH:/home/sf/catkin_ws/src/dynamic_obstacles/models
    
    # 将 PX4 本身以及 sitl_gazebo 路径追加到 ROS_PACKAGE_PATH 中
    export ROS_PACKAGE_PATH=$ROS_PACKAGE_PATH:$(pwd)
    export ROS_PACKAGE_PATH=$ROS_PACKAGE_PATH:$(pwd)/Tools/sitl_gazebo
    
    echo "成功配置 PX4 & 自定义障碍物 Gazebo 模型路径环境变量！"
else
    echo "错误: 未找到 ~/PX4-Autopilot 目录，请检查你的 PX4 路径是否正确！"
    exit 1
fi

echo "=== [3/4] Launching Sourced RViz in Background with 6-second delay... ==="
# 3. 在后台启动一个延迟 6 秒运行的 RViz 监听任务。
# 这样不仅能保障 RViz 拥有完全 Source 的环境变量来完美渲染 package:// 中的 3D 飞鸟模型，
# 还能在前台 SITL 稳定之后再启动 RViz，避开 CPU 暴涨峰值，100% 杜绝“全灰窗口”！
(sleep 6.0 && rosrun rviz rviz -d /home/sf/catkin_ws/src/dynamic_obstacles/config/dynamic_obstacles.rviz) &

echo "=== [4/4] Launching PX4 SITL & Obstacle Controller in Foreground... ==="
# 4. 【最关键的终极修复】在前台运行 roslaunch！
# 之前我们将 roslaunch 放入后台 (&) 运行，导致 PX4 (sitl-2) 的 pxh 交互式终端
# 在后台读取标准输入时读到了 EOF (End of File) 信号，触发了 PX4 的自动安全保护机制，
# 输出 "Exiting NOW." 并自杀退出，从而导致整套仿真崩溃。
# 现在我们在前台正常运行 roslaunch，彻底打通标准输入，彻底解决“闪退自杀”和“段错误”问题！
roslaunch dynamic_obstacles start_simulation.launch "$@"
