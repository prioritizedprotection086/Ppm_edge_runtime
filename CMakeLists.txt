cmake_minimum_required(VERSION 3.16)

project(
    ppm_edge_runtime
    VERSION 0.1.0
    LANGUAGES C
)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

add_library(
    ppm_edge
    Src/Ppm_edge.c
)

target_include_directories(
    ppm_edge
    PUBLIC
    ${PROJECT_SOURCE_DIR}/Src
)

add_executable(
    ppm_demo
    Examples/Basic.c
)

target_link_libraries(
    ppm_demo
    PRIVATE
    ppm_edge
)

enable_testing()
