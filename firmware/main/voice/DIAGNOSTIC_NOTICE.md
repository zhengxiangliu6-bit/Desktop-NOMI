# Public recognition self-test fixture

The build derives official_command.pcm from Espressif esp-sr commit
1c0503e7e2dc5e1ecb2fd3da0a5d7e51e3574842, file
`test_apps/esp-sr/main/samples/da_kai_kong_tiao.h`.
Original repository license (Apache-2.0) is shipped as licenses/ESP-SR.txt.
Source: https://github.com/espressif/esp-sr/blob/1c0503e7e2dc5e1ecb2fd3da0a5d7e51e3574842/test_apps/esp-sr/main/samples/da_kai_kong_tiao.h

This public upstream test phrase means 打开空调. It is fed directly to the local
recognizer during startup, not played through the speaker, and never executes
a face/device command. The temporary diagnostic dictionary is removed before
microphone inference starts. It is not a user recording, custom wake model,
or proof that the board microphone or 小米同学 works.

The derivation script verifies both original header and PCM SHA256. Generated
PCM is ignored by Git; it is embedded for the diagnostic check. No personal
microphone data is stored or sent to the cloud.
