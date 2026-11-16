# Fixed neural spoken response asset (0.5.1)

`okay.pcm` is the literal Chinese response **好的**, generated offline with the public MeloTTS Chinese pretrained female voice (speaker0) through sherpa-onnx2.0.1 CPU. It is an authorized fixed build resource, not user microphone data or a user-targeted cloned voice. Captured audio/transcripts remain excluded from Git and build artifacts.

Upstream: https://github.com/myshell-ai/MeloTTS and https://huggingface.co/myshell-ai/MeloTTS-Chinese (model card declares MIT). The sherpa-onnx converted release explicitly identifies this model as originating from MeloTTS and includes the MyShell.ai MIT notice, reproduced verbatim in `MeloTTS-LICENSE.txt`. sherpa-onnx is Apache-2.0: https://github.com/k2-fsa/sherpa-onnx . Model URL/archive hash/model hash/runtime/settings are recorded in `okay.json`. The 163MiB ONNX model, dictionaries and synthesis runtime are development inputs, not embedded/distributed as firmware runtime dependencies.

Source text `好的。`, source44.1kHz, speaker0, speed1.0; FFmpeg7.1.5 resampling/loudnorm I=-23 TP=-6 LRA5. Final PCM16LE mono16kHz: 8,545 samples, 17,090bytes, 534.0625ms. No voice recording supplied by a user, no per-call TTS charge, no cloud inference, and no runtime TTS engine. Only the fixed waveform is embedded. Exact SHA256 is authoritative; regenerated neural inference is not promised bit-identical.

This replaces the eSpeak-generated0.5.0 clip after user feedback that the sound was unpleasant. Software decoding as “好的” is a content check, not a claim of pleasant sound or physical board verification. Actual loudness/quality/pop/feedback need listening on the board. Synthetic model speech can still sound synthetic; the user should audition before reflashing.
