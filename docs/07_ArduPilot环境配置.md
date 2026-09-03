# 07 ArduPilot 环境配置（飞控切换）

> **适用环境：** Ubuntu 20.04 + Gazebo 11 Classic + ArduPilot
> **目标：** 在保留 PX4 环境的同时，配置一套**相互隔离**的 ArduPilot SITL 环境，可在两种飞控之间切换。

---

## 1. 概述

默认仿真使用 PX4 飞控。为满足切换需求，另配置了一套 ArduPilot（ArduCopter）SITL 环境，通过**独立的环境脚本**与 PX4 隔离，避免 Gazebo 模型/插件路径互相污染。

> 关键原则：**PX4 与 ArduPilot 的环境脚本不要同时 source**，且不要写入 `~/.bashrc`，只在需要时在对应终端里按需加载。

## 2. 相关目录

| 路径 | 说明 |
|------|------|
| `~/ardupilot` | ArduPilot 源码（含 `Tools/autotest/sim_vehicle.py`） |
| `~/ardupilot_gazebo_classic` | Gazebo 11 Classic 插件（`build/`、`models/`、`worlds/`） |
| `~/ardupilot_gazebo` | 新版 ardupilot_gazebo 插件（备用） |
| `~/ardupilot_sim_ws` | 自定义 ArduPilot 仿真工作空间（launch/models/params/worlds 等） |
| `~/venvs/ardupilot-4.5` | ArduPilot 专用 Python 虚拟环境 |

## 3. 环境脚本说明

本包已在 `ardupilot/` 目录整理好三个环境脚本，复制到 `~/` 后按需 `source`：

| 脚本 | 作用 | 使用时机 |
|------|------|----------|
| `ardupilot_env.sh` | 基础环境：加载 Gazebo、`~/ardupilot_gazebo` 插件/模型/世界路径 | 早期 ArduPilot + ardupilot_gazebo 方案 |
| `env_ardupilot_gz11.sh` | 清除 PX4 遗留路径 → 加载 Gazebo 11 + ROS Noetic + `ardupilot-4.5` venv + `ardupilot_gazebo_classic` 插件 | 使用 Gazebo Classic 时 |
| `env_ardupilot_sim.sh` | 在 `env_ardupilot_gz11.sh` 基础上，进一步加载 `~/ardupilot_sim_ws` 的干净模型/世界/插件路径 | **推荐**：干净 ArduPilot 仿真环境 |

推荐用法（只在该终端生效，不影响其他终端的 PX4）：

```bash
source ~/env_ardupilot_sim.sh
```

## 4. 启动流程（标准 ArduPilot SITL + Gazebo Classic）

1. 加载环境：

```bash
source ~/env_ardupilot_sim.sh
```

2. 启动 Gazebo 世界（可选 world：`iris_arducopter_runway.world` / `iris_arducopter_cmac.world`）：

```bash
gazebo --verbose iris_arducopter_runway.world
```

3. 新开终端，启动 ArduPilot SITL：

```bash
sim_vehicle.py -v ArduCopter -f gazebo-iris --console --map
```

> 具体启动命令与机型参数请以实际验证过的为准（`sim_vehicle.py` 位于 `~/ardupilot/Tools/autotest/`，已在环境脚本中加入 PATH）。

## 5. 版本说明（注意核对）

- ArduPilot 源码当前检出标签为 `Copter-4.2.1`（`~/ardupilot`）。
- Python venv 目录名称为 `ardupilot-4.5`，与源码版本命名存在差异，实际以 venv 内依赖为准。
- `ardupilot_gazebo_classic` 为 khancyr/ardupilot_gazebo（上游已标记 Deprecated，推荐新版 `ardupilot_gazebo`），但在 Gazebo 11 Classic + 本项目组合下已验证可用。

## 6. 与 PX4 切换注意事项

- 跑 PX4 的终端：`source ~/setup_all_env.sh`。
- 跑 ArduPilot 的终端：`source ~/env_ardupilot_sim.sh`。
- **不要在同一个终端先后 source 两套脚本**；`env_ardupilot_gz11.sh` 已含清除 PX4 路径的步骤，若混用应先开新终端。
- Gazebo 端口冲突时，先结束残留的 `gzserver`/`gzclient` 进程再启动。

## 7. 常见问题

**问题：ArduPilot 仿真找不到模型/世界**
- 确认已 `source ~/env_ardupilot_sim.sh`，该脚本会设置 `GAZEBO_MODEL_PATH` / `GAZEBO_RESOURCE_PATH` / `GAZEBO_PLUGIN_PATH`。

**问题：sim_vehicle.py 提示 Python 依赖缺失**
- 确认 `~/venvs/ardupilot-4.5` 已激活（脚本会自动 activate），并设置了 `PYTHONNOUSERSITE=1`。
