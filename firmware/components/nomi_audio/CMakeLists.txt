if(NOT NOMI_REPLY_ASSET_DIR)
    set(NOMI_REPLY_ASSET_DIR "${CMAKE_CURRENT_LIST_DIR}/assets")
endif()
idf_component_register(SRCS "audio_input.cpp" INCLUDE_DIRS "include"
 EMBED_FILES "${NOMI_REPLY_ASSET_DIR}/okay.pcm"
 REQUIRES esp_codec_dev esp_driver_i2s esp_driver_i2c esp_driver_gpio)
