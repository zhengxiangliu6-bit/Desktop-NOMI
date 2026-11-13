idf_component_register(SRCS "esp_lcd_st77916.c" "nomi_panel.cpp"
    INCLUDE_DIRS "include" REQUIRES esp_lcd esp_driver_gpio esp_driver_spi esp_driver_ledc lvgl)
