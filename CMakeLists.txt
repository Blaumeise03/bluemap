cmake_minimum_required(VERSION 3.10)

set(CMAKE_CXX_STANDARD 20)

# Set the project name
project(eve-mapper)

# Add the cpp directory to the list of include directories
include_directories(${PROJECT_SOURCE_DIR}/cpp)

# Find all .cpp files in the cpp directory
file(GLOB CPP_SOURCES "${PROJECT_SOURCE_DIR}/cpp/*.cpp")

# Download stb_image_write.h and link it to the project
file(DOWNLOAD "https://raw.githubusercontent.com/nothings/stb/master/stb_image_write.h" "${PROJECT_SOURCE_DIR}/cpp/stb_image_write.h")

# Add the executable
add_executable(evemapper ${CPP_SOURCES})
add_compile_definitions(EVE_MAPPER_DEBUG_LOG)
add_compile_definitions(EVE_MAPPER_LINK_STB)