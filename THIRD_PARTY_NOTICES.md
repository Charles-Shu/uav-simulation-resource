# 第三方内容声明（Third-Party Notices）

本仓库仅包含**原创内容**（文档、世界文件、自建障碍物/无人机模型、ROS 功能包、环境脚本）。以下第三方内容**不随本仓库分发**，请按链接自行获取，并遵守各自的开源许可。

## 一、传感器驱动 / 仿真插件（需自行 clone 并编译）

| 组件 | 用途 | 来源 | 许可 |
|------|------|------|------|
| [Livox-SDK2](https://github.com/Livox-SDK/Livox-SDK2) | Livox 雷达 SDK | GitHub | 见上游 |
| [livox_ros_driver2](https://github.com/Livox-SDK/livox_ros_driver2) | Mid-360 ROS 驱动 | GitHub | MIT |
| [Mid360_imu_sim](https://github.com/qiurongcan/Mid360_imu_sim)（livox_laser_simulation 分支） | Mid-360 Gazebo 仿真插件 + 扫描文件 | GitHub | MIT |
| [realsense_ros_gazebo](https://gitee.com/nie_xun/realsense_ros_gazebo) | D435i Gazebo 仿真插件 | Gitee | **未声明（请自行核实）** |

> 安装步骤见 [docs/02_传感器搭载_mid360_D435i.md](docs/02_传感器搭载_mid360_D435i.md)。编译产物 `.so` 亦不随仓库分发。

## 二、模型 / 网格资源

| 内容 | 来源 | 说明 |
|------|------|------|
| `Mid360` / `D435i` 等传感器模型 | 来自上述第三方插件包 | 安装插件包后自动获得 |
| 树模型（`worlds/models/` 下 oak/pine） | 来源待确认 | 供 `scene_00000.world` 引用，请自行获取 |
| ARGO 海鸥模型 | 3D Warehouse | **3D Warehouse 模型通常不允许再分发，已从仓库排除** |
| Matrice 100 机体网格（`models/uav/*/meshes/`） | DJI 官方模型 | 请确认再分发许可后再用于公开发布 |

## 三、使用建议

- 若需要**开箱即用的完整离线包**（含上述第三方内容），请使用原交付目录打包的 `simulation_resource.tar.gz`（不在本仓库内）。
- 对外公开发布前，请确认 `realsense_ros_gazebo`、ARGO 海鸥模型、DJI Matrice 100 网格的许可是否允许再分发。
