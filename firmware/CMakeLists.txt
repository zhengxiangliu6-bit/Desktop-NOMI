cmake_minimum_required(VERSION 3.16)
set(IDF_TARGET esp32s3)
set(ENV{IDF_COMPONENT_MANAGER} "0")
set(COMPONENTS main)
set(EXTRA_COMPONENT_DIRS
    "${CMAKE_CURRENT_LIST_DIR}/.deps/esp-sr"
    "${CMAKE_CURRENT_LIST_DIR}/.deps/espressif__esp-dsp"
    "${CMAKE_CURRENT_LIST_DIR}/.deps/esp-adf/components/esp_codec_dev")
include($ENV{IDF_PATH}/tools/cmake/project.cmake)
include($ENV{IDF_PATH}/tools/cmake/version.cmake)
if(NOT "$ENV{IDF_VERSION}" STREQUAL "5.5.4")
    message(FATAL_ERROR "H2 requires ESP-IDF 5.5.4; found $ENV{IDF_VERSION}")
endif()
project(desktop_nomi_h2 VERSION 0.5.0)
