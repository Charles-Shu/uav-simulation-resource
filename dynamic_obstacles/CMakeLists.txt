cmake_minimum_required(VERSION 3.0.2)
project(dynamic_obstacles)

find_package(catkin REQUIRED COMPONENTS
  roscpp
  rospy
  std_msgs
  geometry_msgs
  gazebo_msgs
)

catkin_package()

catkin_install_python(PROGRAMS
  scripts/obstacle_controller.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)
