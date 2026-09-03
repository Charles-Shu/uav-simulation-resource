# 无人机仿真环境资源包

本目录是一套**可交付、可复现**的无人机仿真环境资源，覆盖从环境搭建、场景建模、传感器搭载到动态障碍物仿真、飞控切换（PX4 / ArduPilot）的全过程。接收方按文档步骤即可在一台全新的 Ubuntu 机器上复现同样的仿真环境。

## 一、环境版本矩阵

| 组件 | 版本 | 说明 |
|------|------|------|
| 操作系统 | Ubuntu 20.04 | x86_64 |
| ROS | ROS Noetic | ROS1 |
| 仿真器 | Gazebo 11 Classic | 非 Ignition/Garden |
| 飞控（主） | PX4 v1.13.0 | 需用对应版本的工具链 |
| 飞控（备） | ArduPilot | 与 PX4 环境隔离使用 |
| 地面站 | QGroundControl | V4.4.4 及以前版本 |
| 主要传感器 | Livox Mid-360（激光雷达）、Intel RealSense D435i（深度相机） | 均已适配仿真 |

## 二、目录结构

```
simulation_resource/
├── README.md                    # 本文件（总览）
├── docs/                        # 说明文档
│   ├── 01_仿真环境搭建.md
│   ├── 02_传感器搭载_mid360_D435i.md
│   ├── 03_世界场景使用.md
│   ├── 04_静态障碍物与地形模型.md
│   ├── 05_无人机与传感器模型.md
│   ├── 06_动态障碍物仿真.md
│   └── 07_ArduPilot环境配置.md
├── worlds/                      # 自定义世界场景功能包（原 my_gazebo_worlds）
│   ├── worlds/*.world           # 世界文件
│   └── models/                  # 场景引用的树/地形模型
├── models/                      # 自定义模型（复制到 PX4 模型库）
│   ├── terrain_obstacles/       # 沙地/水体/高压线塔等静态障碍物
│   ├── sensors/                 # Mid360 / D435i 等传感器
│   └── uav/                     # iris / matrice_100 系列无人机
├── dynamic_obstacles/           # 动态障碍物 ROS 功能包
├── sensor_plugins/              # 传感器源码包 + 已编译插件
│   ├── compiled/                # 可直接使用的 .so 插件
│   ├── Mid360_imu_sim/
│   ├── realsense_ros_gazebo/
│   └── livox_ros_driver2/
├── ardupilot/                   # ArduPilot 环境脚本
├── scripts/                     # setup_all_env.sh 一键环境脚本
└── MANIFEST.txt                 # 完整文件清单（供核对）
```

## 三、快速上手（三步）

1. **搭环境**：按 [01_仿真环境搭建.md](docs/01_仿真环境搭建.md) 安装 ROS / PX4 / MAVROS / QGroundControl，并配置一键环境脚本。
2. **装传感器与无人机**：按 [02_传感器搭载_mid360_D435i.md](docs/02_传感器搭载_mid360_D435i.md) 编译 Mid-360 与 D435i 驱动插件，再按 [05_无人机与传感器模型.md](docs/05_无人机与传感器模型.md) 选择要用的无人机模型。
3. **跑仿真**：按 [03_世界场景使用.md](docs/03_世界场景使用.md) 选择世界场景并启动；需要动态障碍物则看 [06_动态障碍物仿真.md](docs/06_动态障碍物仿真.md)。

## 四、文档导航

| 文档 | 内容 |
|------|------|
| [01_仿真环境搭建.md](docs/01_仿真环境搭建.md) | ROS Noetic + PX4 v1.13 + MAVROS + QGC 完整安装 |
| [02_传感器搭载_mid360_D435i.md](docs/02_传感器搭载_mid360_D435i.md) | Mid-360 / D435i 驱动、插件编译与搭载 |
| [03_世界场景使用.md](docs/03_世界场景使用.md) | 世界文件原理、切换方法、已有场景清单 |
| [04_静态障碍物与地形模型.md](docs/04_静态障碍物与地形模型.md) | 沙地/水体/高压线塔等模型说明与使用 |
| [05_无人机与传感器模型.md](docs/05_无人机与传感器模型.md) | iris / matrice_100 系列无人机模型清单 |
| [06_动态障碍物仿真.md](docs/06_动态障碍物仿真.md) | 动态障碍物功能包的使用与交互控制 |
| [07_ArduPilot环境配置.md](docs/07_ArduPilot环境配置.md) | ArduPilot 飞控环境（与 PX4 隔离） |

## 五、文件归置对照表

接收方拿到本包后，按下列对应关系把文件放回标准位置：

| 本包路径 | 放回位置 | 说明 |
|----------|----------|------|
| `worlds/` | `~/catkin_ws/src/my_gazebo_worlds/` | 整个目录，保持为 catkin 功能包 |
| `models/terrain_obstacles/*`、`models/sensors/*`、`models/uav/*` | `~/PX4-Autopilot/Tools/sitl_gazebo/models/` | 每个子目录是一个模型 |
| `dynamic_obstacles/` | `~/catkin_ws/src/dynamic_obstacles/` | ROS 功能包 |
| `sensor_plugins/Mid360_imu_sim` 等三个源码包 | `~/catkin_ws/src/` | 编译生成插件 |
| `sensor_plugins/compiled/*.so` | `~/catkin_ws/devel/lib/` | 或 `~/PX4-Autopilot/build/px4_sitl_default/build_gazebo/` |
| `ardupilot/*.sh` | `~/` | ArduPilot 环境脚本 |
| `scripts/setup_all_env.sh` | `~/` | PX4 一键环境脚本 |

## 六、第三方依赖（开源仓库版）

本仓库**只包含原创内容**（文档、世界文件、自建障碍物/无人机模型、ROS 功能包、环境脚本）。以下第三方内容不随仓库分发，请按 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) 中的链接自行获取：

- 传感器驱动与仿真插件：Livox-SDK2、livox_ros_driver2、Mid360_imu_sim、realsense_ros_gazebo
- 传感器模型（Mid360 / D435i 等）、世界场景引用的树模型、3D Warehouse 海鸥模型（ARGO）

> 若需要**开箱即用的完整离线包**（含上述第三方内容），请使用原交付目录打包的 `simulation_resource.tar.gz`（不在此仓库内）。

## 七、注意事项

- 所有文档中的路径统一以 `~/`（即 `/home/<用户名>/`）表示，请按自己机器的实际用户名替换。示例基于 `/home/sf`。
- 传感器插件（`.so`）为已编译二进制，仅适用于 Ubuntu 20.04 + ROS Noetic + Gazebo 11 环境；换环境请按 [02_传感器搭载_mid360_D435i.md](docs/02_传感器搭载_mid360_D435i.md) 从源码重新编译。
- `models/` 下保留了建模过程中的**全部中间版本与备份文件**（如 `Mid360#.sdf`、`iris_mid360_D435i_2.0/3.0/4.0` 等），正式使用时请优先选用文档标注的最终版。
