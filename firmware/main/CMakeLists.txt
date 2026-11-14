idf_component_register(SRCS "main.cpp" "face_model.cpp" "face_view.cpp" "wake/wake_word_controller.cpp"
 INCLUDE_DIRS "." "wake" REQUIRES nomi_panel nomi_audio esp-sr espressif__esp-dsp lvgl esp_timer esp_psram esp_driver_usb_serial_jtag)
target_compile_features(${COMPONENT_LIB} PUBLIC cxx_std_17)
