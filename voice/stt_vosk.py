import os
os.environ["VOSK_LOG_LEVEL"] = "0"

import queue
import json
import time

import sounddevice as sd
from vosk import Model, KaldiRecognizer
from core.config import load_config


class SpeechToText:
    def __init__(self):
        cfg = load_config()

        self.sample_rate = cfg["audio"]["sample_rate"]
        self.max_seconds = cfg["stt"].get("max_seconds", 8)
        self.channels = cfg["audio"]["channels"]

        self.model = Model(cfg["stt"]["vosk_model_path"])
        self.device = cfg["audio"].get("input_device")

        self.q = queue.Queue()

    def _callback(self, indata, frames, time_info, status):
        if status:
            return
        # IMPORTANT: convert to bytes explicitly
        self.q.put(bytes(indata))

    def listen_once(self) -> str:
        rec = KaldiRecognizer(self.model, self.sample_rate)
        start = time.time()

        with sd.RawInputStream(
            samplerate=self.sample_rate,
            blocksize=4000,           # SMALLER blocks → better speech detection
            dtype="int16",
            channels=self.channels,
            device=self.device,       # EXPLICIT device (or default)
            callback=self._callback,
        ):
            while True:
                if time.time() - start > self.max_seconds:
                    # fallback to partial result
                    partial = json.loads(rec.PartialResult()).get("partial", "")
                    return partial.strip()

                data = self.q.get()

                if rec.AcceptWaveform(data):
                    result = json.loads(rec.Result())
                    return result.get("text", "").strip()
