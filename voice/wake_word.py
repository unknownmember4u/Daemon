import os
os.environ["VOSK_LOG_LEVEL"] = "0"


import queue
import sounddevice as sd
from vosk import Model, KaldiRecognizer
from core.config import load_config



class WakeWordListener:
    def __init__(self):
        cfg = load_config()
        self.sample_rate = cfg["audio"]["sample_rate"]
        model_path = cfg["stt"]["vosk_model_path"]
        wake_word = cfg["assistant"]["wake_word"]

        self.model = Model(model_path)
        grammar = '["hey daemon"]'

        self.rec = KaldiRecognizer(self.model, self.sample_rate, grammar)

        self.q = queue.Queue()

    def _callback(self, indata, frames, time, status):
        if status:
            return
        self.q.put(bytes(indata))
        print(f"DEBUG: WakeWordListener received audio data, size: {len(indata)}") # Debugging: Confirm audio data is received

    def wait(self):
        print("DEBUG: WakeWordListener is waiting for wake word...")
        with sd.RawInputStream(
            samplerate=self.sample_rate,
            blocksize=8000,
            dtype="int16",
            channels=1,
            callback=self._callback,
        ):
            while True:
                data = self.q.get()
                if self.rec.AcceptWaveform(data):
                    return True
