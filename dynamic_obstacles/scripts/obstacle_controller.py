#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import rospy
import rospkg
import os
import math
import re
import random
from gazebo_msgs.srv import SpawnModel, DeleteModel
from gazebo_msgs.msg import ModelState, ModelStates
from geometry_msgs.msg import Pose, Point, Quaternion, Twist, Vector3, PoseStamped
from std_msgs.msg import String
from visualization_msgs.msg import Marker, MarkerArray

def euler_to_quaternion(roll, pitch, yaw):
    """Convert roll, pitch, yaw to quaternion."""
    cy = math.cos(yaw * 0.5)
    sy = math.sin(yaw * 0.5)
    cp = math.cos(pitch * 0.5)
    sp = math.sin(pitch * 0.5)
    cr = math.cos(roll * 0.5)
    sr = math.sin(roll * 0.5)

    q = Quaternion()
    q.w = cr * cp * cy + sr * sp * sy
    q.x = sr * cp * cy - cr * sp * sy
    q.y = cr * sp * cy + sr * cp * sy
    q.z = cr * cp * sy - sr * sp * cy
    return q

class DynamicObstaclesController:
    def __init__(self):
        rospy.init_node('dynamic_obstacles_controller', anonymous=True)
        
        # Get package path
        rospack = rospkg.RosPack()
        self.package_path = rospack.get_path('dynamic_obstacles')
        
        # Automatically patch the bird model color & strip white wireframes on startup!
        self.auto_patch_dae()
        
        # Read parameters
        self.num_drones_param = rospy.get_param('~num_drones', 6)
        self.num_birds_param = rospy.get_param('~num_birds', 6)
        
        # Mode and Obstacle Speed (target_speed is for high-speed RViz intercept)
        self.control_mode = rospy.get_param('~control_mode', 'interactive')
        self.target_speed = rospy.get_param('~target_speed', 6.0) 
        self.random_flight_speed = 2.0 # Relaxed cruising speed for background random flight
        
        rospy.loginfo(f"Mode: {self.control_mode.upper()} | Intercept Speed: {self.target_speed} m/s | Cruise Speed: {self.random_flight_speed} m/s")

        # Ros service clients
        rospy.loginfo("Waiting for Gazebo services...")
        rospy.wait_for_service('/gazebo/spawn_sdf_model')
        rospy.wait_for_service('/gazebo/delete_model')
        self.spawn_client = rospy.ServiceProxy('/gazebo/spawn_sdf_model', SpawnModel)
        self.delete_client = rospy.ServiceProxy('/gazebo/delete_model', DeleteModel)
        rospy.loginfo("Gazebo services connected!")

        # Publisher to update model states fast and non-blocking
        self.state_pub = rospy.Publisher('/gazebo/set_model_state', ModelState, queue_size=10)

        # Publisher for RViz visualization markers (Drones and Seagulls visible in RViz!)
        self.marker_pub = rospy.Publisher('/obstacle_markers', MarkerArray, queue_size=10)

        # Subscriber for RViz "2D Nav Goal" click event
        self.goal_sub = rospy.Subscriber('/move_base_simple/goal', PoseStamped, self.rviz_goal_cb)
        
        # Subscriber for manual selection of active obstacle
        self.select_sub = rospy.Subscriber('/select_obstacle', String, self.select_obstacle_cb)
        self.selected_obstacle_name = ""

        # Initialize obstacle configurations list
        self.obstacles_config = []
        
        # Full master pool of 15 drone coordinate centers (spread over a 120m x 120m area)
        drone_centers_pool = [
            (25.0, 0.0, 4.5, 'circle', {'radius': 6.0, 'omega': 0.15, 'osc_amp': 0.3}),
            (-25.0, 20.0, 6.0, 'circle', {'radius': 5.0, 'omega': -0.2, 'osc_amp': 0.5}),
            (0.0, 30.0, 5.5, 'eight', {'A': 8.0, 'B': 4.0, 'omega': 0.1, 'osc_amp': 0.2}),
            (-15.0, -30.0, 7.0, 'eight', {'A': 6.0, 'B': 6.0, 'omega': 0.12, 'osc_amp': 0.4}),
            (20.0, -25.0, 5.0, 'linear', {'length': 8.0, 'angle': math.pi/4, 'omega': 0.18, 'osc_amp': 0.3}),
            (-35.0, -10.0, 6.5, 'circle', {'radius': 7.0, 'omega': 0.14, 'osc_amp': 0.2}),
            (35.0, 25.0, 7.5, 'eight', {'A': 10.0, 'B': 5.0, 'omega': 0.08, 'osc_amp': 0.3}),
            (-5.0, -5.0, 3.5, 'linear', {'length': 6.0, 'angle': -math.pi/3, 'omega': 0.22, 'osc_amp': 0.1}),
            (45.0, -15.0, 8.0, 'circle', {'radius': 5.5, 'omega': -0.16, 'osc_amp': 0.4}),
            (-45.0, 35.0, 5.0, 'linear', {'length': 9.0, 'angle': math.pi/6, 'omega': 0.15, 'osc_amp': 0.3}),
            (50.0, 10.0, 6.0, 'circle', {'radius': 6.5, 'omega': 0.13, 'osc_amp': 0.2}),
            (-50.0, -20.0, 5.5, 'eight', {'A': 7.0, 'B': 7.0, 'omega': 0.11, 'osc_amp': 0.3}),
            (10.0, 50.0, 7.0, 'linear', {'length': 8.0, 'angle': -math.pi/4, 'omega': 0.16, 'osc_amp': 0.4}),
            (-20.0, -50.0, 4.0, 'circle', {'radius': 5.0, 'omega': -0.18, 'osc_amp': 0.2}),
            (30.0, -50.0, 5.0, 'linear', {'length': 10.0, 'angle': math.pi/2, 'omega': 0.14, 'osc_amp': 0.3})
        ]
        
        # Limit to the requested parameter size
        num_drones = min(self.num_drones_param, len(drone_centers_pool))
        drone_centers = drone_centers_pool[:num_drones]
        
        for i, (x0, y0, z0, traj, spec) in enumerate(drone_centers):
            idx = i + 1
            params = {
                'x0': x0, 'y0': y0, 'z0': z0,
                'phase': (idx * math.pi / 5.0) % (2 * math.pi)
            }
            params.update(spec)
            self.obstacles_config.append({
                'name': f'obs_drone_{idx}',
                'type': 'iris_obstacle',
                'traj': traj,
                'params': params,
                # Dynamic properties
                'curr_x': x0, 'curr_y': y0, 'curr_z': z0, 'curr_yaw': 0.0,
                'target_x': x0, 'target_y': y0, 'target_z': z0, 'is_active': False,
                # Random flight variables (Cruises around a local 20m box of its spawn center)
                'rand_target_x': x0, 'rand_target_y': y0, 'rand_target_z': z0,
                'spawn_x': x0, 'spawn_y': y0, 'spawn_z': z0
            })
            
        # Full master pool of 15 bird coordinate centers (slightly higher altitude: 6.5m to 13.0m)
        bird_centers_pool = [
            (10.0, -10.0, 8.0, 'circle', {'radius': 4.5, 'omega': 0.25, 'osc_amp': 0.2}),
            (-20.0, -15.0, 9.5, 'linear', {'length': 10.0, 'angle': -math.pi/6, 'omega': 0.15, 'osc_amp': 0.4}),
            (-10.0, 45.0, 11.0, 'circle', {'radius': 5.0, 'omega': -0.22, 'osc_amp': 0.3}),
            (30.0, -35.0, 10.0, 'eight', {'A': 7.0, 'B': 3.5, 'omega': 0.13, 'osc_amp': 0.2}),
            (-40.0, -25.0, 8.5, 'circle', {'radius': 6.0, 'omega': 0.18, 'osc_amp': 0.3}),
            (40.0, 10.0, 9.0, 'linear', {'length': 7.0, 'angle': math.pi/2, 'omega': 0.2, 'osc_amp': 0.3}),
            (-30.0, 15.0, 10.5, 'eight', {'A': 9.0, 'B': 4.5, 'omega': 0.09, 'osc_amp': 0.4}),
            (15.0, 35.0, 12.0, 'circle', {'radius': 5.5, 'omega': -0.17, 'osc_amp': 0.5}),
            (-15.0, 15.0, 7.5, 'linear', {'length': 8.0, 'angle': math.pi/3, 'omega': 0.16, 'osc_amp': 0.2}),
            (50.0, -45.0, 11.5, 'eight', {'A': 8.0, 'B': 8.0, 'omega': 0.11, 'osc_amp': 0.3}),
            (-50.0, 40.0, 10.0, 'circle', {'radius': 6.0, 'omega': 0.14, 'osc_amp': 0.4}),
            (50.0, 30.0, 12.5, 'linear', {'length': 9.0, 'angle': -math.pi/3, 'omega': 0.12, 'osc_amp': 0.3}),
            (-35.0, -45.0, 9.0, 'eight', {'A': 8.0, 'B': 4.0, 'omega': 0.15, 'osc_amp': 0.2}),
            (0.0, -50.0, 11.0, 'circle', {'radius': 5.0, 'omega': -0.2, 'osc_amp': 0.3}),
            (-45.0, -5.0, 13.0, 'linear', {'length': 10.0, 'angle': 0.0, 'omega': 0.1, 'osc_amp': 0.4})
        ]
        
        # Limit to the requested parameter size
        num_birds = min(self.num_birds_param, len(bird_centers_pool))
        bird_centers = bird_centers_pool[:num_birds]
        
        for i, (x0, y0, z0, traj, spec) in enumerate(bird_centers):
            idx = i + 1
            params = {
                'x0': x0, 'y0': y0, 'z0': z0,
                'phase': (idx * math.pi / 4.0) % (2 * math.pi)
            }
            params.update(spec)
            self.obstacles_config.append({
                'name': f'obs_bird_{idx}',
                'type': 'ARGO',  # 真实海鸥模型
                'traj': traj,
                'params': params,
                # Dynamic properties
                'curr_x': x0, 'curr_y': y0, 'curr_z': z0, 'curr_yaw': 0.0,
                'target_x': x0, 'target_y': y0, 'target_z': z0, 'is_active': False,
                # Random flight variables (Cruises around a local 20m box of its spawn center)
                'rand_target_x': x0, 'rand_target_y': y0, 'rand_target_z': z0,
                'spawn_x': x0, 'spawn_y': y0, 'spawn_z': z0
            })

        # Keep track of successfully spawned models
        self.spawned_models = []

        # Register shutdown hook to delete models
        rospy.on_shutdown(self.cleanup)

    def auto_patch_dae(self):
        """
        1. 自动剥离 DAE 文件中的 <lines> 线框元素，让遮挡海鸥高清材质贴图的白色网格棱边彻底消失！
        2. 自动修正 DAE 文件中默认的 SketchUp 灰色鸟嘴与爪子颜色为高饱和度的金黄色。
        3. 确保真实的黑色眼睛和完美翼尖材质正常显示。
        """
        # Supports both path layouts natively to prevent warnings
        dae_path_1 = os.path.join(self.package_path, 'models', 'ARGO', 'model.dae')
        dae_path_2 = os.path.join(self.package_path, 'ARGO', 'model.dae')
        
        dae_path = dae_path_1 if os.path.exists(dae_path_1) else dae_path_2
        
        if not os.path.exists(dae_path):
            rospy.logwarn(f"DAE mesh not found at {dae_path_1} or {dae_path_2}. Skipping auto-patch.")
            return
            
        try:
            with open(dae_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # 1. 使用正则表达式剥离所有 <lines> 标签极其内容（清除白色的网格线框）
            if "<lines" in content:
                rospy.loginfo("Stripping wireframe lines from ARGO seagull DAE model...")
                content = re.sub(r'<lines[^>]*>.*?</lines>', '', content, flags=re.DOTALL)
                
            # 2. SketchUp 导出的 DAE 默认物体的颜色修正（RGBA 米灰色）：0.9019608 0.854902 0.7529412
            old_color = "0.9019608 0.854902 0.7529412"
            # 亮橘黄色 (RGB 255 170 0)
            new_color = "1.0 0.666 0.0"
            
            if old_color in content:
                rospy.loginfo("Auto-patching ARGO seagull DAE model texture colors...")
                content = content.replace(old_color, new_color)
                
            with open(dae_path, 'w', encoding='utf-8') as f:
                f.write(content)
            rospy.loginfo("Successfully patched bird meshes! White edges removed and beak/claws turned golden yellow!")
        except Exception as e:
            rospy.logwarn(f"Failed to auto-patch DAE file: {e}")

    def select_obstacle_cb(self, msg):
        """Callback to manually select an active obstacle via ROS topic."""
        name = msg.data.strip()
        found = False
        for obs in self.obstacles_config:
            if obs['name'] == name:
                self.selected_obstacle_name = name
                rospy.loginfo(f"Obstacle '{name}' manually selected for RViz guidance!")
                found = True
                break
        if not found:
            rospy.logwarn(f"Selected obstacle name '{name}' is not spawned in this simulation.")

    def rviz_goal_cb(self, msg):
        """
        Callback when '2D Nav Goal' button is clicked in RViz.
        If an obstacle is manually selected via /select_obstacle, we fly that obstacle.
        Otherwise, we automatically pick the TOP 3 NEAREST obstacles to fly together as a swarm (甲方新需求 3)！
        """
        goal_x = msg.pose.position.x
        goal_y = msg.pose.position.y
        
        if not self.spawned_models:
            rospy.logwarn("No obstacles spawned in simulation yet.")
            return

        # 1. Manual selection mode
        if self.selected_obstacle_name in self.spawned_models:
            for obs in self.obstacles_config:
                if obs['name'] == self.selected_obstacle_name:
                    obs['target_x'] = goal_x
                    obs['target_y'] = goal_y
                    obs['is_active'] = True
                    rospy.loginfo(f"RViz Manual Command: '{obs['name']}' flying to [{goal_x:.2f}, {goal_y:.2f}, {obs['target_z']:.1f}]")
                    return

        # 2. Swarm Threat Injection mode (Automatically fly the TOP 3 closest obstacles as a flock!)
        obstacles_with_dist = []
        for obs in self.obstacles_config:
            if obs['name'] in self.spawned_models:
                dist = math.sqrt((obs['curr_x'] - goal_x)**2 + (obs['curr_y'] - goal_y)**2)
                obstacles_with_dist.append((dist, obs))
        
        # Sort by distance
        obstacles_with_dist.sort(key=lambda x: x[0])
        
        # Select up to 3 closest obstacles
        target_group = [item[1] for item in obstacles_with_dist[:3]]
        
        rospy.loginfo(f"RViz Swarm Threat Injection: Dispatched {len(target_group)} closest obstacles to fly as a flock!")
        
        # Group spatial separation configuration (so they don't overlap)
        # Offset them in a small triangular formation around the goal point
        offsets = [
            (0.0, 0.0), # Leader right on target
            (2.0, 0.0), # Left wingman offset
            (-1.0, 1.7) # Right wingman offset
        ]
        
        for i, obs in enumerate(target_group):
            dx, dy = offsets[i % len(offsets)]
            obs['target_x'] = goal_x + dx
            obs['target_y'] = goal_y + dy
            obs['is_active'] = True
            
            rospy.loginfo(f" -> '{obs['name']}' intercepted and redirected to offset [{obs['target_x']:.1f}, {obs['target_y']:.1f}]...")

    def generate_new_random_target(self, obs):
        """
        Generates a new random cruising waypoint within a 25m horizontal box and 3m vertical window
        relative to its original spawn center. This keeps obstacles naturally patrolling their territory.
        """
        box_radius = 15.0 # Cruise within +/- 15m horizontally
        z_window = 1.5    # Cruise within +/- 1.5m vertically
        
        obs['rand_target_x'] = obs['spawn_x'] + random.uniform(-box_radius, box_radius)
        obs['rand_target_y'] = obs['spawn_y'] + random.uniform(-box_radius, box_radius)
        obs['rand_target_z'] = obs['spawn_z'] + random.uniform(-z_window, z_window)
        
        # Keep safe minimum flight altitude
        if obs['rand_target_z'] < 2.5:
            obs['rand_target_z'] = 2.5

    def update_obstacle_state(self, obs, dt):
        """
        Comprehensive state machine for each obstacle.
        - Case 1 (ACTIVE / INTERCEPT): Smoothly fly toward RViz nav goal at high 'self.target_speed'.
          Once arrived (distance < 0.8m), automatically clear active state and return to random cruising
          starting from this new coordinate! (甲方新需求：截击完成后，原地继续进行无限随机飞行)
        - Case 2 (IDLE / CRUISE): Cruise towards local 'rand_target' at relaxed 'self.random_flight_speed'.
          Once arrived (distance < 1.0m), generate a new random local target.
        """
        curr_x, curr_y, curr_z = obs['curr_x'], obs['curr_y'], obs['curr_z']
        
        if obs['is_active']:
            # --- Case 1: Active Intercept mode (6.0m/s, guided by RViz goal) ---
            target_x, target_y, target_z = obs['target_x'], obs['target_y'], obs['target_z']
            speed = self.target_speed
            arrival_threshold = 0.8
        else:
            # --- Case 2: Natural Random Cruising mode (2.0m/s, cruising randomly) ---
            # If random target is too close or uninitialized, generate a new one
            dx_r = obs['rand_target_x'] - curr_x
            dy_r = obs['rand_target_y'] - curr_y
            dz_r = obs['rand_target_z'] - curr_z
            r_dist = math.sqrt(dx_r**2 + dy_r**2 + dz_r**2)
            
            if r_dist < 1.0:
                self.generate_new_random_target(obs)
                
            target_x, target_y, target_z = obs['rand_target_x'], obs['rand_target_y'], obs['rand_target_z']
            speed = self.random_flight_speed
            arrival_threshold = 1.0

        # Compute translation vectors
        dx = target_x - curr_x
        dy = target_y - curr_y
        dz = target_z - curr_z
        
        dist = math.sqrt(dx**2 + dy**2 + dz**2)
        
        vx, vy, vz, wz = 0.0, 0.0, 0.0, 0.0
        
        if dist > arrival_threshold:
            # Fly toward current target
            ux = dx / dist
            uy = dy / dist
            uz = dz / dist
            
            vx = speed * ux
            vy = speed * uy
            vz = speed * uz
            
            obs['curr_x'] += vx * dt
            obs['curr_y'] += vy * dt
            obs['curr_z'] += vz * dt
            
            # Smoothly face the flight direction (Yaw)
            target_yaw = math.atan2(vy, vx)
            dyaw = target_yaw - obs['curr_yaw']
            dyaw = (dyaw + math.pi) % (2 * math.pi) - math.pi
            
            # Constrain yaw rate to prevent rapid snapping
            max_wz = 2.5
            wz = dyaw / dt
            if abs(wz) > max_wz:
                wz = math.copysign(max_wz, wz)
                
            obs['curr_yaw'] += wz * dt
            obs['curr_yaw'] = (obs['curr_yaw'] + math.pi) % (2 * math.pi) - math.pi
        else:
            # Arrived at target
            if obs['is_active']:
                # Intercept finished! Hand control back to random flight from this new location
                obs['is_active'] = False
                obs['spawn_x'] = curr_x # Update spawn center to current position so it cruises here!
                obs['spawn_y'] = curr_y
                obs['spawn_z'] = curr_z
                self.generate_new_random_target(obs)
                rospy.loginfo(f" -> '{obs['name']}' arrived at intercept. Returning to random cruising from this position.")
            else:
                # Cruise point reached, generate next waypoint
                self.generate_new_random_target(obs)
                
        return obs['curr_x'], obs['curr_y'], obs['curr_z'], obs['curr_yaw'], vx, vy, vz, wz

    def load_sdf(self, model_type):
        """Loads and returns the SDF content for a given model type."""
        sdf_path = os.path.join(self.package_path, 'models', model_type, 'model.sdf')
        if not os.path.exists(sdf_path):
            rospy.logerr(f"SDF file not found: {sdf_path}")
            return None
        with open(sdf_path, 'r') as f:
            return f.read()

    def wait_for_main_drone(self):
        """Waits for the main drone 'iris' to spawn first."""
        rospy.loginfo("======================================================")
        rospy.loginfo("Waiting for the main drone 'iris' to appear in Gazebo...")
        rospy.loginfo("======================================================")
        
        start_wait_time = rospy.get_time()
        main_drone_found = False
        
        while not rospy.is_shutdown():
            try:
                msg = rospy.wait_for_message('/gazebo/model_states', ModelStates, timeout=2.0)
                if any(name.startswith('iris') for name in msg.name):
                    rospy.loginfo("Main drone 'iris' detected in Gazebo!")
                    main_drone_found = True
                    break
            except rospy.ROSException:
                pass
            
            elapsed = rospy.get_time() - start_wait_time
            if elapsed > 25.0:
                rospy.logwarn("Timeout waiting for 'iris' model to spawn. Proceeding to spawn obstacles...")
                break
                
            rospy.sleep(0.5)
            
        if main_drone_found:
            rospy.loginfo("Waiting 4.0 seconds for Gazebo physics and world rendering to fully stabilize...")
            rospy.sleep(4.0)

    def spawn_single_obstacle(self, obs):
        """Spawns a single obstacle model in Gazebo."""
        name = obs['name']
        model_type = obs['type']
        
        # Load the corresponding SDF
        sdf_xml = self.load_sdf(model_type)
        if sdf_xml is None:
            return

        # Calculate initial position
        x_init, y_init, z_init, yaw_init = self.get_pose_at_time(obs, 0.0)
        
        # Update current positions
        obs['curr_x'] = x_init
        obs['curr_y'] = y_init
        obs['curr_z'] = z_init
        obs['curr_yaw'] = yaw_init
        obs['target_x'] = x_init
        obs['target_y'] = y_init
        obs['target_z'] = z_init

        pose = Pose()
        pose.position = Point(x_init, y_init, z_init)
        pose.orientation = euler_to_quaternion(0, 0, yaw_init)

        try:
            resp = self.spawn_client(
                model_name=name,
                model_xml=sdf_xml,
                robot_namespace='',
                initial_pose=pose,
                reference_frame='world'
            )
            if resp.success:
                self.spawned_models.append(name)
                rospy.loginfo(f"Successfully spawned: {name} ({model_type}) at [{x_init:.1f}, {y_init:.1f}, {z_init:.1f}]")
            else:
                rospy.logwarn(f"Failed to spawn {name}: {resp.status_message}")
        except rospy.ServiceException as e:
            rospy.logwarn(f"Service call failed for spawning {name}: {e}")

    def spawn_all_obstacles(self):
        """Spawns all configured obstacles sequentially with a slight delay."""
        rospy.loginfo(f"Spawning {len(self.obstacles_config)} dynamic obstacles gradually...")
        for obs in self.obstacles_config:
            if rospy.is_shutdown():
                break
            self.spawn_single_obstacle(obs)
            rospy.sleep(0.3)
        rospy.loginfo("All dynamic obstacles successfully loaded!")

    def get_pose_at_time(self, obs, t):
        """Calculates 3D position and yaw of an obstacle at any given time t (analytical)."""
        traj = obs['traj']
        p = obs['params']
        
        x, y, z = 0.0, 0.0, 0.0
        yaw = 0.0

        if traj == 'circle':
            theta = p['omega'] * t + p['phase']
            x = p['x0'] + p['radius'] * math.cos(theta)
            y = p['y0'] + p['radius'] * math.sin(theta)
            z = p['z0'] + p['osc_amp'] * math.sin(2 * theta)
            
            vx = -p['radius'] * p['omega'] * math.sin(theta)
            vy = p['radius'] * p['omega'] * math.cos(theta)
            yaw = math.atan2(vy, vx)

        elif traj == 'eight':
            theta = p['omega'] * t + p['phase']
            x = p['x0'] + p['A'] * math.sin(theta)
            y = p['y0'] + p['B'] * math.sin(2 * theta)
            z = p['z0'] + p['osc_amp'] * math.cos(theta)
            
            vx = p['A'] * p['omega'] * math.cos(theta)
            vy = 2 * p['B'] * p['omega'] * math.cos(2 * theta)
            yaw = math.atan2(vy, vx)

        elif traj == 'linear':
            theta = p['omega'] * t + p['phase']
            dist = p['length'] * math.sin(theta)
            x = p['x0'] + dist * math.cos(p['angle'])
            y = p['y0'] + dist * math.sin(p['angle'])
            z = p['z0'] + p['osc_amp'] * math.cos(theta)
            
            v_scalar = p['length'] * p['omega'] * math.cos(theta)
            if v_scalar >= 0:
                yaw = p['angle']
            else:
                yaw = p['angle'] + math.pi

        return x, y, z, yaw

    def compute_state_and_twist(self, obs, t):
        """Computes position and twist at time t (for auto-trajectory mode)."""
        dt = 0.001
        x, y, z, yaw = self.get_pose_at_time(obs, t)
        x_next, y_next, z_next, yaw_next = self.get_pose_at_time(obs, t + dt)

        vx = (x_next - x) / dt
        vy = (y_next - y) / dt
        vz = (z_next - z) / dt

        dyaw = yaw_next - yaw
        dyaw = (dyaw + math.pi) % (2 * math.pi) - math.pi
        wz = dyaw / dt
        
        obs['curr_x'] = x
        obs['curr_y'] = y
        obs['curr_z'] = z
        obs['curr_yaw'] = yaw

        return x, y, z, yaw, vx, vy, vz, wz

    def publish_rviz_markers(self):
        """Publishes 3D mesh markers (and labels) for all obstacles."""
        marker_array = MarkerArray()
        
        for i, obs in enumerate(self.obstacles_config):
            name = obs['name']
            if name not in self.spawned_models:
                continue
                
            # 1. Mesh Marker (Show the actual 3D Seagull and 3D drone in RViz!)
            mesh_marker = Marker()
            mesh_marker.header.frame_id = "map"
            mesh_marker.header.stamp = rospy.Time.now()
            mesh_marker.ns = "obstacle_meshes"
            mesh_marker.id = i
            mesh_marker.action = Marker.ADD
            
            mesh_marker.pose.position.x = obs['curr_x']
            mesh_marker.pose.position.y = obs['curr_y']
            mesh_marker.pose.position.z = obs['curr_z']
            mesh_marker.pose.orientation = euler_to_quaternion(0, 0, obs['curr_yaw'])
            
            if obs['type'] == 'ARGO':
                mesh_marker.type = Marker.MESH_RESOURCE
                mesh_marker.mesh_resource = "package://dynamic_obstacles/models/ARGO/model.dae"
                mesh_marker.scale = Vector3(0.0254, 0.0254, 0.0254)
                mesh_marker.color.r = 0.0  
                mesh_marker.color.g = 0.0
                mesh_marker.color.b = 0.0
                mesh_marker.color.a = 0.0  # 0.0 tells RViz to use mesh texture colors!
            else:
                mesh_marker.type = Marker.SPHERE
                mesh_marker.scale = Vector3(0.6, 0.6, 0.2)
                mesh_marker.color.r = 1.0  # Bright Red
                mesh_marker.color.g = 0.0
                mesh_marker.color.b = 0.0
                mesh_marker.color.a = 0.9
                
            marker_array.markers.append(mesh_marker)
            
            # 2. Text Label Marker
            text_marker = Marker()
            text_marker.header.frame_id = "map"
            text_marker.header.stamp = rospy.Time.now()
            text_marker.ns = "obstacle_labels"
            text_marker.id = i + 1000
            text_marker.type = Marker.TEXT_VIEW_FACING
            text_marker.action = Marker.ADD
            
            text_marker.pose.position.x = obs['curr_x']
            text_marker.pose.position.y = obs['curr_y']
            text_marker.pose.position.z = obs['curr_z'] + 0.6
            
            text_marker.text = f"{name}"
            text_marker.scale.z = 0.6
            text_marker.color.r = 1.0
            text_marker.color.g = 1.0
            text_marker.color.b = 1.0
            text_marker.color.a = 1.0
            
            marker_array.markers.append(text_marker)
            
        self.marker_pub.publish(marker_array)

    def run(self):
        """Main loop."""
        self.wait_for_main_drone()
        self.spawn_all_obstacles()
        
        hz = 50
        rate = rospy.Rate(hz)
        dt = 1.0 / hz
        start_time = rospy.Time.now()
        
        marker_timer = 0

        rospy.loginfo(f"Dynamic obstacles controller active in {self.control_mode.upper()} mode.")
        while not rospy.is_shutdown():
            current_time = (rospy.Time.now() - start_time).to_sec()

            for obs in self.obstacles_config:
                name = obs['name']
                if name not in self.spawned_models:
                    continue

                if self.control_mode == 'interactive':
                    # Interactive Mode (Random Cruise by default, Click & Fly group intercept, return to Random Cruise)
                    x, y, z, yaw, vx, vy, vz, wz = self.update_obstacle_state(obs, dt)
                else:
                    # Trajectory Mode
                    x, y, z, yaw, vx, vy, vz, wz = self.compute_state_and_twist(obs, current_time)

                state_msg = ModelState()
                state_msg.model_name = name
                state_msg.pose.position = Point(x, y, z)
                state_msg.pose.orientation = euler_to_quaternion(0, 0, yaw)
                state_msg.twist.linear = Vector3(vx, vy, vz)
                state_msg.twist.angular = Vector3(0.0, 0.0, wz)
                state_msg.reference_frame = 'world'

                self.state_pub.publish(state_msg)

            # Publish RViz visualization markers at 10Hz to save bandwidth
            marker_timer += 1
            if marker_timer >= 5:
                self.publish_rviz_markers()
                marker_timer = 0

            rate.sleep()

    def cleanup(self):
        """Deletes all spawned obstacle models when the node is shut down."""
        rospy.loginfo("Cleaning up: Deleting dynamic obstacle models from Gazebo...")
        for name in list(self.spawned_models):
            try:
                resp = self.delete_client(model_name=name)
                if resp.success:
                    self.spawned_models.remove(name)
            except Exception:
                pass
        rospy.loginfo("Dynamic obstacles cleanup complete.")

if __name__ == '__main__':
    try:
        controller = DynamicObstaclesController()
        controller.run()
    except rospy.ROSInterruptException:
        pass
