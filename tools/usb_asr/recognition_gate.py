"""Pause/reset streaming ASR across explicitly flagged device playback, without dropping transport frames."""
class RecognitionGate:
    def __init__(self,report):
        self.guarding=False
        self.report=report

    def feed(self,recognizer,pcm,guarded):
        if guarded!=self.guarding:
            recognizer.reset()
            self.guarding=guarded
            self.report('播放保护','暂停识别，避免自己的回应回灌；请等说完再讲话' if guarded else '恢复识别')
        return [] if guarded else recognizer.feed(pcm)
