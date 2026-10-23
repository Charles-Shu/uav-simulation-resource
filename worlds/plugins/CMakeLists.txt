cmake_minimum_required(VERSION 3.10)
project(portable_scene_plugins LANGUAGES CXX)

find_package(PkgConfig REQUIRED)
pkg_check_modules(GAZEBO REQUIRED IMPORTED_TARGET gazebo)
if(GAZEBO_VERSION VERSION_LESS 11 OR NOT GAZEBO_VERSION VERSION_LESS 12)
  message(FATAL_ERROR "LakeWaterPlugin requires Gazebo Classic 11; found ${GAZEBO_VERSION}")
endif()

add_library(LakeWaterPlugin SHARED LakeWaterPlugin.cc)
target_compile_features(LakeWaterPlugin PRIVATE cxx_std_17)
target_compile_options(LakeWaterPlugin PRIVATE -Wall -Wextra)
target_link_libraries(LakeWaterPlugin PRIVATE PkgConfig::GAZEBO)
set_target_properties(LakeWaterPlugin PROPERTIES
  CXX_EXTENSIONS OFF
  LIBRARY_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}"
)
foreach(config DEBUG RELEASE RELWITHDEBINFO MINSIZEREL)
  set_target_properties(LakeWaterPlugin PROPERTIES
    LIBRARY_OUTPUT_DIRECTORY_${config} "${CMAKE_BINARY_DIR}"
  )
endforeach()
