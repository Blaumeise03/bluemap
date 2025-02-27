cmake_minimum_required(VERSION 3.10)

set(CMAKE_CXX_STANDARD 20)

# Set the project name
project(eve-mapper)

# Add the cpp directory to the list of include directories
include_directories(${PROJECT_SOURCE_DIR}/cpp)

# Find all .cpp files in the cpp directory
file(GLOB CPP_SOURCES "${PROJECT_SOURCE_DIR}/cpp/*.cpp")

# Add the executable
add_executable(evemapper ${CPP_SOURCES})
add_compile_definitions(EVE_MAPPER_DEBUG_LOG)