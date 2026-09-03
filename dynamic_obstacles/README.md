# Dynamic Obstacles Simulation Package (for PX4 & Gazebo Classic & ROS1)

这是为 PX4、Gazebo Classic 和 ROS 1 开发的轻量级、高逼真、高度可控的动态障碍物仿真管理包。

---

## 🚀 核心升级特性（满足甲方最新需求）

1. **导入 3D Warehouse 真实海鸥模型 (`ARGO`)**
   - **格式原生支持**：Gazebo 不需要将 `.dae` 转换成 `.sdf`！我们通过编写通用的 `model.sdf` 和 `model.config`，让 Gazebo 直接加载 `.dae` 真实网格与 JPEG 贴图。
   - **完美缩放尺寸**：自动处理了 SketchUp 导出的英寸 (inch) 转米 (meter) 缩放问题（`0.0254` 比例），海鸥将 100% 显形，且尺寸极具真实感！

2. **RViz 交互式“指哪飞哪”战术指引模式 (Interactive Click-to-Fly)**
   - **打通控制话题**：系统默认启动 `interactive` 模式。20 个障碍物在启动时会静态加载在天空中。
   - **一键指挥飞行**：在 RViz 界面上方点击 **"2D Nav Goal"** 并在地图上点击任意位置，**离该位置最近的障碍物（无人机或海鸥）会立即以极具真实感的飞行姿态（自动调头、平滑加速）飞向你点击的目标点！**
   - **手动指名选取**：支持向话题 `/select_obstacle` (String) 发送特定的名字（如 `"obs_drone_2"` 或 `"obs_bird_1"`）来手动锁定要指挥的特定障碍物。
   - **验证避障绝佳**：这允许测试人员在仿真过程中，随时手动“指挥”任意一个障碍物飞向主无人机，在动态逼近中极限测试感知与避障算法！

3. **速度大幅提升**
   - 障碍物的飞行速度从两三米每秒大幅提升为 **$6.0\text{m/s}$（可调）**，平滑调头与加速，满足高速情况下的感知避障验证。

---

## 📂 目录结构
```
dynamic_obstacles/
├── CMakeLists.txt
├── package.xml
├── README.md
├── run_simulation.sh            # 自动配置环境 + 自动重置/杀死僵尸进程的一键启动脚本
├── launch/
│   └── start_simulation.launch  # 核心 Launch 文件，支持参数 num_drones, num_birds, control_mode, target_speed
├── models/
│   ├── iris_obstacle/           # 亮红色 / 官方 STL 样式的轻量级 iris 障碍物
│   │   ├── model.config
│   │   └── model.sdf
│   └── ARGO/                    # 甲方要求的 3D Warehouse 真实海鸥模型
│       ├── model.config
│       ├── model.sdf            # 核心 SDF 配置
│       ├── model.dae            # 海鸥 3D 骨骼网格
│       └── model/               # 贴图图片文件夹
│           ├── ARGO_seagull02_0.jpg
│           ├── ARGO_seagull02.jpg
│           └── ARGO_seagull03.jpg
└── scripts/
    └── obstacle_controller.py   # 解析 50Hz 交互式轨迹 / 自动调头朝向 / 瞬时速度计算
```

---

## 📥 部署步骤

### 第一步：将海鸥模型移动到指定路径
确保你的 `ARGO` 模型文件夹位于 `dynamic_obstacles/models/ARGO` 下。
其完整结构应为：
```bash
~/catkin_ws/src/dynamic_obstacles/models/ARGO/model.config (我已为你建好)
~/catkin_ws/src/dynamic_obstacles/models/ARGO/model.sdf    (我已为你写好)
~/catkin_ws/src/dynamic_obstacles/models/ARGO/model.dae
~/catkin_ws/src/dynamic_obstacles/models/ARGO/model/       (贴图文件夹)
```

### 第二步：将整个功能包覆盖拷贝至工作空间
```bash
# 拷贝到你的 catkin 工作空间 src 目录下
cp -r /home/user/dynamic_obstacles ~/catkin_ws/src/
```

### 第三步：编译工作空间
```bash
cd ~/catkin_ws
catkin_make
source devel/setup.bash
```

---

## 🎮 如何运行仿真与交互控制？

### 1. 运行一键启动脚本
直接执行脚本，默认启动交互模式，飞行速度 $6.0\text{m/s}$（共 6架无人机 + 6只 ARGO海鸥）：
```bash
~/catkin_ws/src/dynamic_obstacles/run_simulation.sh
```

*(如果你电脑配置好，想要拉满 10+10 的规模，只需运行：)*
```bash
~/catkin_ws/src/dynamic_obstacles/run_simulation.sh num_drones:=10 num_birds:=10 target_speed:=8.0
```

### 2. 在 RViz 中操控障碍物飞行！
Gazebo 和你的 RViz 打开后：
1. 观察 RViz 界面，会看到静态分布在天空中的障碍物。
2. 点击 RViz 上方工具栏中的 **"2D Nav Goal"** 按钮。
3. **在地图中任意一个地方点击一下。**
4. 奇迹发生了：**离你点击位置最近的那只海鸥或无人机会立刻平滑地旋转机身/鸟身，以 6m/s 的高速度流畅、笔直地飞向你指定的地点！**
5. 再次点击，又可以控制另一个距离最近的障碍物。
6. **手动锁定控制（可选）**：如果你想指定 `obs_drone_3` 去飞，你只需新开终端发布名字到选择话题：
   ```bash
   rostopic pub -1 /select_obstacle std_msgs/String "data: 'obs_drone_3'"
   ```
   然后你在 RViz 再次点击 "2D Nav Goal" 时，**必定只有 `obs_drone_3` 会飞过去**，无论距离远近。
7. **恢复自由航迹模式**：如果你仍想让他们像以前那样绕圈、飞八字，只需启动时切换模式即可：
   ```bash
   ~/catkin_ws/src/dynamic_obstacles/run_simulation.sh control_mode:=trajectory
   ```
