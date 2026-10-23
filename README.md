# 无人机仿真环境资源包

本仓库包含无人机仿真环境资源与搭建文档，覆盖场景建模、传感器搭载、动态障碍物和飞控集成（PX4 / ArduPilot）。其中新增的 **3 个 1 km × 1 km 场景**按可移植方式打包：世界文件、22 个运行模型目录、贴图、物理插件源码和可编辑 Blender 工程均放在仓库内。

## 先运行三个可移植场景

基本运行只需要 **Gazebo Classic 11**；ROS Noetic、PX4 和 Blender 均为可选组件。首次使用山湖或城市河流场景时，需要 C++ 编译器、CMake、pkg-config、Python 3 和 Gazebo 11 开发文件，以便在本机编译水体插件。

克隆后在仓库根目录执行：

```bash
git clone https://github.com/Charles-Shu/uav-simulation-resource.git
cd uav-simulation-resource
python3 tools/validate_scene_assets.py  # 只检查资产路径与依赖，无需 Gazebo
./scripts/prepare_scenes.sh            # 检查资产并编译水体插件
./scripts/run_scene.sh snow           # 雪山
# 或者分别启动：
./scripts/run_scene.sh mountain       # 山地湖泊、树林
./scripts/run_scene.sh city           # 城市、河流、桥梁、树林及原创输电走廊
```

上面的场景启动命令是备选项，每次选择一个。`snow` 不需要水体插件，可直接启动；`mountain`、`city` 会在插件缺失时自动调用准备脚本。脚本从自身位置计算路径，支持带空格的克隆目录，不修改 `.bashrc`，也不下载或安装依赖。

| 别名 | 正式世界文件 | Blender 工程 |
|---|---|---|
| `snow` | `worlds/worlds/alpine_snow_1km.world` | `scene_sources/alpine_snow_1km/blender/alpine_snow_1km.blend` |
| `mountain` | `worlds/worlds/mountain_lakes_1km.world` | `scene_sources/mountain_lakes_1km/blender/mountain_lakes_1km.blend` |
| `city` | `worlds/worlds/urban_river_1km.world` | `scene_sources/urban_river_1km/blender/urban_river_1km.blend` |

完整操作、起飞高度、ROS/PX4 接入、Blender 编辑和物理限制见 **[三个场景使用指南](docs/scenes/README.md)**。这些世界提供环境，不会自动生成无人机。新增场景的依赖检查范围不包括仓库中其他历史世界。

## 一、环境版本矩阵

下表保留完整飞控与传感器工作流的版本参考；仅运行上面的三个场景时，以场景指南列出的最小依赖为准。

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
│   ├── 07_ArduPilot环境配置.md
│   └── scenes/README.md         # 新增三个可移植场景指南
├── worlds/                      # 自定义世界场景功能包（原 my_gazebo_worlds）
│   ├── worlds/*.world           # 世界文件
│   ├── models/                  # 三个场景所需的 22 个模型目录
│   ├── plugins/                 # LakeWaterPlugin.cc 与独立 CMake 工程
│   ├── launch/scene.launch      # 可选 ROS 入口
│   └── .scene-build/            # 本机生成的插件，Git 忽略
├── scene_sources/               # 三个场景的编辑与重建资料
│   └── <场景名>/                # blender/、source_textures/、地形数据等
├── tools/                       # 资产检查、Blender 导入、原创输电塔生成
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
├── scripts/                     # scene_env/prepare_scenes/run_scene 与历史环境脚本
└── MANIFEST.txt                 # 完整文件清单（供核对）
```

此目录图同时保留历史完整交付包的布局。公开仓库不携带 `sensor_plugins/`、第三方传感器模型等全部内容；是否随库分发以[第三方声明](THIRD_PARTY_NOTICES.md)为准。三个新增场景使用的模型位于 `worlds/models/`，无需复制到个人 Gazebo 模型缓存。

## 三、完整飞控与传感器工作流（三步）

1. **搭环境**：按 [01_仿真环境搭建.md](docs/01_仿真环境搭建.md) 安装 ROS / PX4 / MAVROS / QGroundControl，并配置一键环境脚本。
2. **装传感器与无人机**：按 [02_传感器搭载_mid360_D435i.md](docs/02_传感器搭载_mid360_D435i.md) 编译 Mid-360 与 D435i 驱动插件，再按 [05_无人机与传感器模型.md](docs/05_无人机与传感器模型.md) 选择要用的无人机模型。
3. **跑仿真**：按 [03_世界场景使用.md](docs/03_世界场景使用.md) 选择世界场景并启动；需要动态障碍物则看 [06_动态障碍物仿真.md](docs/06_动态障碍物仿真.md)。

## 四、文档导航

| 文档 | 内容 |
|------|------|
| [三个场景使用指南](docs/scenes/README.md) | 雪山 / 山湖 / 城市的独立运行、ROS/PX4 接入、源文件及物理范围 |
| [01_仿真环境搭建.md](docs/01_仿真环境搭建.md) | ROS Noetic + PX4 v1.13 + MAVROS + QGC 完整安装 |
| [02_传感器搭载_mid360_D435i.md](docs/02_传感器搭载_mid360_D435i.md) | Mid-360 / D435i 驱动、插件编译与搭载 |
| [03_世界场景使用.md](docs/03_世界场景使用.md) | 世界文件原理、切换方法、已有场景清单 |
| [04_静态障碍物与地形模型.md](docs/04_静态障碍物与地形模型.md) | 沙地/水体/高压线塔等模型说明与使用 |
| [05_无人机与传感器模型.md](docs/05_无人机与传感器模型.md) | iris / matrice_100 系列无人机模型清单 |
| [06_动态障碍物仿真.md](docs/06_动态障碍物仿真.md) | 动态障碍物功能包的使用与交互控制 |
| [07_ArduPilot环境配置.md](docs/07_ArduPilot环境配置.md) | ArduPilot 飞控环境（与 PX4 隔离） |

## 五、文件归置对照表

以下是历史完整工作流的文件归置参考。新增的三个场景优先使用仓库内脚本，不必移动文件；若通过 ROS 使用，可按[场景指南](docs/scenes/README.md)临时设置 `ROS_PACKAGE_PATH`。

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

本仓库包含原创代码、文档、地形与场景布局，也随新增三个场景分发了具有相应许可的第三方资源：Poly Haven 地表贴图、Fuel 建筑、Kenney 建筑，以及 OSRF 的树和住宅模型。**原创内容采用根目录 MIT 许可；第三方资源保留其 CC0 或 CC BY 3.0 许可，并不因进入本仓库而统一变为 MIT。** 详细来源与署名见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

以下内容仍不随仓库分发，需按第三方声明中的链接获取：

- 传感器驱动与仿真插件：Livox-SDK2、livox_ros_driver2、Mid360_imu_sim、realsense_ros_gazebo
- 传感器模型（Mid360 / D435i 等）、3D Warehouse 海鸥模型（ARGO）

城市场景使用本项目原创的 `uav_power_corridor`，替换了许可不明确、不可随公开场景再分发的本地输电塔资源；运行这三个世界不依赖那份本地模型。

> 历史交付目录可能另有 `simulation_resource.tar.gz`，不在本仓库内，其内容和许可范围应单独核对。运行新增三个场景无需该归档；编译器、Gazebo 等系统依赖仍需预先安装。

## 七、注意事项

- 历史文档包含 `~/` 和作者机器路径，接入完整飞控环境时应按本机实际位置调整。新增三场景的启动脚本从仓库位置自动解析运行资源。
- 历史离线交付包中的传感器插件（`.so`）具有系统和 ABI 依赖；公开仓库不携带这些二进制，需按 [02_传感器搭载_mid360_D435i.md](docs/02_传感器搭载_mid360_D435i.md) 编译。新增水体插件也在目标机器上编译，不提交 `.so`。
- `models/` 下保留了建模过程中的**全部中间版本与备份文件**（如 `Mid360#.sdf`、`iris_mid360_D435i_2.0/3.0/4.0` 等），正式使用时请优先选用文档标注的最终版。
