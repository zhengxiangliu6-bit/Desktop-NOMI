idf_component_register(SRCS "main.cpp" "face_model.cpp" "face_view.cpp"
    INCLUDE_DIRS "." REQUIRES nomi_panel lvgl esp_timer esp_psram esp_driver_usb_serial_jtag)
target_compile_features(${COMPONENT_LIB} PUBLIC cxx_std_17)
