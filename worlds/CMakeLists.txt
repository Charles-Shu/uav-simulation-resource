cmake_minimum_required(VERSION 3.0.2)
project(my_gazebo_worlds)
find_package(catkin REQUIRED)
catkin_package()
# The scene package is used from its source/devel space. Build the water plugin
# with ../scripts/prepare_scenes.sh; binaries stay outside version control.
