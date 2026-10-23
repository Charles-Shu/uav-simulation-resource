# 第三方内容声明（Third-Party Notices）

本仓库同时包含原创内容和第三方资源。根目录 [LICENSE](LICENSE) 的 MIT 许可适用于项目原创代码、文档、场景布局、原创地形几何和原创模型；第三方模型、纹理及其衍生资产仍受各自许可约束。Blender 工程将这些资产组合到同一场景中，不改变各资产的许可。

## 一、随三个可移植场景分发的资源

三个正式世界及其模型位于 `worlds/worlds/`、`worlds/models/`，编辑资料位于 `scene_sources/`。运行资源包括 22 个模型目录；同一模型可以在世界中出现多个实例。

| 内容 | 来源与作者 | 许可 | 随包记录 |
|---|---|---|---|
| 雪、岩石、草、泥、沙、沥青与混凝土等地表纹理 | [Poly Haven](https://polyhaven.com/)；各贴图作者见下方逐场景清单 | CC0-1.0 | 各场景的 `source_textures/SOURCES.md`、`sources.json`、原始纹理和部分 API 记录 |
| `oak_tree`、`pine_tree` | Louise Poubel；[OSRF gazebo_models](https://github.com/osrf/gazebo_models/tree/8163eb4b5e7e21985c6591d1c0bfb56468c0093f) | CC BY 3.0 Unported | 每个模型的 `ATTRIBUTION.md` 与 `LICENSE` |
| `house_1`、`house_2`、`house_3` | Cole Biesemeyer；同一 OSRF 上游 | CC BY 3.0 Unported | 每个模型的 `ATTRIBUTION.md` 与 `LICENSE` |
| `apartment`、`law_office` | Nate Koenig；Open Robotics Fuel 的 [Apartment](https://app.gazebosim.org/OpenRobotics/fuel/models/Apartment)、[Law office](https://app.gazebosim.org/OpenRobotics/fuel/models/Law%20office) | CC0-1.0，依据对应 Fuel 模型记录 | 每个模型的 `ATTRIBUTION.md` 与 `LICENSE_SOURCE.json` |
| `kenney_skyscraper_a` 至 `kenney_skyscraper_e` | Kenney，[City Kit Commercial](https://kenney.nl/assets/city-kit-commercial) | CC0-1.0 | 每个模型的 `LICENSE.txt` |
| `uav_power_corridor` | 本项目原创，`tools/generate_power_corridor.py` 生成 | MIT | 根目录许可及生成脚本说明 |
| 三个地形、`urban_infrastructure` 和 `urban_*` 程序生成建筑 | 本项目原创几何与布局；其中使用的第三方贴图按原许可保留 | 原创部分 MIT；第三方纹理 CC0-1.0 | 地形源数据、脚本与贴图来源记录 |
| `LakeWaterPlugin.cc` | Mountain Lakes scene contributors | MIT | [worlds/plugins/LICENSE](worlds/plugins/LICENSE) |

### 地表贴图逐场景清单

- [雪山贴图来源](scene_sources/alpine_snow_1km/source_textures/SOURCES.md)：包括 `snow_02`、`aerial_rocks_04`、`aerial_grass_rock`、`brown_mud`、`rock_boulder_dry` 等。
- [山湖贴图来源](scene_sources/mountain_lakes_1km/source_textures/SOURCES.md)：包括 `leafy_grass`、`grass_ground`、`sand_01`、`sand_02` 及复用的岩石和泥土贴图。
- [城市贴图来源](scene_sources/urban_river_1km/source_textures/SOURCES.md)：另包括 `clean_asphalt`、`concrete_pavement_02`、`rough_concrete`。

Poly Haven 的逐资源作者包括 Rob Tuytel、Charlotte Baglioni、Dimitrios Savva 和 Rico Cilliers；具体作者、下载地址及文件校验信息以各场景来源清单为准。参考 [Poly Haven 许可说明](https://polyhaven.com/license) 与 [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/)。运行时使用的地表合成/烘焙纹理源于这些资产。

### OSRF 模型署名与修改说明

树和住宅模型按 [Creative Commons Attribution 3.0 Unported](https://creativecommons.org/licenses/by/3.0/) 分发。请在再分发这些模型或包含它们的场景时保留作者、来源、许可及修改说明；各模型目录已经提供署名文件。上游仓库许可副本为 [docs/scenes/OSRF_MODELS_LICENSE.txt](docs/scenes/OSRF_MODELS_LICENSE.txt)，核对记录为 [docs/scenes/osrf_source_verification.json](docs/scenes/osrf_source_verification.json)。

本次打包保留上述模型的几何、纹理和碰撞定义，资源 URI/纹理路径按仓库布局做可移植处理。Fuel、Kenney 建筑也可能包含格式转换、资源路径调整和实例布局；这些操作不改变原资源的 CC0 许可。

### 原创输电走廊

公开城市场景使用 `uav_power_corridor`：原创杆塔、绝缘子和有弧垂的导线几何，由项目脚本生成。它替换了本地旧场景中未获明确再分发许可的输电塔模型。旧塔及其网格不作为这三个公开场景的依赖，也不能用根目录 MIT 许可替代其原始授权。

## 二、传感器驱动 / 仿真插件（不随仓库分发，需自行 clone 并编译）

| 组件 | 用途 | 来源 | 许可 |
|------|------|------|------|
| [Livox-SDK2](https://github.com/Livox-SDK/Livox-SDK2) | Livox 雷达 SDK | GitHub | 见上游 |
| [livox_ros_driver2](https://github.com/Livox-SDK/livox_ros_driver2) | Mid-360 ROS 驱动 | GitHub | MIT |
| [Mid360_imu_sim](https://github.com/qiurongcan/Mid360_imu_sim)（livox_laser_simulation 分支） | Mid-360 Gazebo 仿真插件 + 扫描文件 | GitHub | MIT |
| [realsense_ros_gazebo](https://gitee.com/nie_xun/realsense_ros_gazebo) | D435i Gazebo 仿真插件 | Gitee | **未声明（请自行核实）** |

> 安装步骤见 [docs/02_传感器搭载_mid360_D435i.md](docs/02_传感器搭载_mid360_D435i.md)。编译产物 `.so` 亦不随仓库分发。

## 三、历史工作流中的其他模型 / 网格资源

| 内容 | 来源 | 说明 |
|------|------|------|
| `Mid360` / `D435i` 等传感器模型 | 来自上述第三方插件包 | 安装插件包后自动获得 |
| 新增场景使用的树与住宅模型 | OSRF，见第一节 | 已随库分发并附 CC BY 3.0 许可和署名；其他历史世界的全部依赖仍需单独核对 |
| ARGO 海鸥模型 | 3D Warehouse | **3D Warehouse 模型通常不允许再分发，已从仓库排除** |
| Matrice 100 机体网格（`models/uav/*/meshes/`） | DJI 官方模型 | 请确认再分发许可后再用于公开发布 |

## 四、使用范围

- 三个新增场景的运行资源已经随库提供；系统依赖和本机编译的插件不在资源包内。它们不依赖传感器驱动、ARGO 或 DJI 机体网格。
- 历史 `simulation_resource.tar.gz` 不在本仓库内，其资源清单和许可不能用本文件替代。
- 需要使用或再分发历史工作流中的 `realsense_ros_gazebo`、ARGO、DJI Matrice 100 等资源时，应核对对应上游授权；本次三场景打包不替这些资源新增许可。
