# ESP-IDF resolves component requirements before loading sdkconfig.
set(wifi_requirements esp_wifi esp_netif esp_event esp_http_client mbedtls nvs_flash json)
idf_component_register(SRCS "main.cpp" "voice/wifi_voice.cpp" "face_model.cpp" "face_view.cpp" "wake/wake_word_controller.cpp" "voice/command_recognizer.cpp" "stream/usb_audio_stream.cpp" "stream/audio_trace.cpp"
 INCLUDE_DIRS "." "wake" "voice" "stream" REQUIRES nomi_panel nomi_audio esp-sr espressif__esp-dsp lvgl esp_timer esp_psram esp_driver_usb_serial_jtag vfs PRIV_REQUIRES ${wifi_requirements})
target_compile_features(${COMPONENT_LIB} PUBLIC cxx_std_17)

if(CONFIG_NOMI_VOICE_COMMANDS)
    target_add_binary_data(${COMPONENT_LIB} "${CMAKE_CURRENT_LIST_DIR}/../.generated/official_command.pcm" BINARY)
endif()
