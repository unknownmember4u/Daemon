import queue
import sounddevice as sd
import json
from vosk import Model, KaldiRecognizer
from core.config import load_config

class SpeechToText:
    def __init__(self):
        cfg = load_config()
        self.sample_rate = cfg["audio"]["sample_rate"]
        model_path = cfg["stt"]["vosk_model_path"]
        self.model = Model(model_path)

    def _callback(self, indata, frames, time, status):
        if status:
            return
        self.q.put(bytes(indata))

    def listen_once(self):
        self.q = queue.Queue()
        rec = KaldiRecognizer(self.model, self.sample_rate)

        with sd.RawInputStream(
            samplerate=self.sample_rate,
            blocksize=8000,
            dtype="int16",
            channels=1,
            callback=self._callback,
        ):
            while True:
                data = self.q.get()
                if rec.AcceptWaveform(data):
                    result = json.loads(rec.Result())
                    text = result.get("text", "").strip()
                    if text:
                        return text
