"""Local CPU ASR. Accepts PCM from the board only; never opens a computer microphone."""
import numpy as np
import sherpa_onnx


class ChineseRecognizer:
    def __init__(self, model, threads=2):
        self.engine = sherpa_onnx.OnlineRecognizer.from_zipformer2_ctc(
            tokens=str(model/'tokens.txt'), model=str(model/'model.int8.onnx'),
            num_threads=threads, sample_rate=16000, enable_endpoint_detection=True,
            rule1_min_trailing_silence=2.4, rule2_min_trailing_silence=0.9,
            rule3_min_utterance_length=20, provider='cpu', debug=False)
        self.stream = self.engine.create_stream()
        self.previous = ''

    def feed(self, pcm):
        samples = np.frombuffer(pcm, dtype='<i2').astype(np.float32)/32768.0
        self.stream.accept_waveform(16000, samples)
        while self.engine.is_ready(self.stream):
            self.engine.decode_stream(self.stream)
        text = self.engine.get_result(self.stream).strip()
        events = []
        if text and text != self.previous:
            events.append(('临时', text))
            self.previous = text
        if self.engine.is_endpoint(self.stream):
            events.append(('最终', text) if text else ('状态', '本段无识别文字（不能据此判断没有声音）'))
            self.engine.reset(self.stream)
            self.previous = ''
        return events

    def finish(self):
        # Flush decoder context only; appended zeros are not represented as real microphone input.
        self.stream.accept_waveform(16000, np.zeros(8000, dtype=np.float32))
        self.stream.input_finished()
        while self.engine.is_ready(self.stream):
            self.engine.decode_stream(self.stream)
        text = self.engine.get_result(self.stream).strip()
        return [('最终', text)] if text else []
