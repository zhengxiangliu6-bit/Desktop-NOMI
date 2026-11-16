# Fixed spoken response asset

`okay.pcm` is a project-generated synthetic pronunciation of the literal Chinese text **好的**. It is not a recording of a user or a cloned human voice. The user's fixed spoken-response request authorizes this narrow playback resource; captured microphone audio remains excluded from Git/build artifacts.

Generated offline using `espeakng-loader` 0.2.4 / eSpeak NG 1.52.0, voice `cmn`, speech rate150. Development postprocessing: FFmpeg7.1.5, mono16kHz PCM16LE, loudnorm I=-23/TP=-6/LRA=5. Runtime firmware contains only the fixed PCM samples, not an eSpeak/TTS engine or arbitrary text synthesis. The generator/tool binaries are not distributed in the firmware. eSpeak NG is GPL-3.0-or-later; upstream source and license: https://github.com/espeak-ng/espeak-ng . This notice records provenance and does not relabel the engine's license.

Exact format, duration/count and SHA256 are in `okay.json`. Duration492.6875ms, 15,766bytes. The clip was decoded as “好的” by the pinned local ASR in a software check; this does not verify the board loudspeaker, audible quality, loudness, or acoustic feedback suppression on physical hardware.
