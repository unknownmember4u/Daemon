import os
os.environ["VOSK_LOG_LEVEL"] = "0"

import queue
import json
import sounddevice as sd
from vosk import Model, KaldiRecognizer
from core.config import load_config


class WakeWordListener:
    def __init__(self):
        cfg = load_config()
        self.sample_rate = cfg["audio"]["sample_rate"]
        self.channels = cfg["audio"].get("channels", 1)
        self.device = cfg["audio"].get("input_device")
        model_path = cfg["stt"]["vosk_model_path"]
        self.wake_word = cfg["assistant"]["wake_word"].lower()

        # Phonetic variants for "daemon" in standard English Vosk model dictionary
        self.wake_variants = ["daemon", "demon", "damon", "daymon", "diamond", "damen"]

        self.model = Model(model_path)
        self.rec = KaldiRecognizer(self.model, self.sample_rate)
        self.q = queue.Queue()

    def _callback(self, indata, frames, time, status):
        if status:
            return
        self.q.put(bytes(indata))

    def _check_text(self, text: str) -> bool:
        text = text.lower().strip()
        if not text:
            return False

        if self.wake_word in text:
            return True

        words = text.split()
        if any(w in words for w in ["hey", "hi", "hello"]):
            if any(v in words for v in self.wake_variants):
                return True
        elif any(v in words for v in self.wake_variants):
            return True

        return False

    def wait(self):
        print(f"DEBUG: WakeWordListener is waiting for wake word ('{self.wake_word}')...")
        while not self.q.empty():
            try:
                self.q.get_nowait()
            except queue.Empty:
                break

        with sd.RawInputStream(
            samplerate=self.sample_rate,
            blocksize=4000,
            dtype="int16",
            channels=self.channels,
            device=self.device,
            callback=self._callback,
        ):
            while True:
                data = self.q.get()
                if self.rec.AcceptWaveform(data):
                    res = json.loads(self.rec.Result())
                    text = res.get("text", "").strip()
                    if text:
                        print(f"DEBUG: WakeWordListener heard: '{text}'")
                    if self._check_text(text):
                        print(f"DEBUG: Wake word detected in '{text}'!")
                        return True
                else:
                    partial = json.loads(self.rec.PartialResult())
                    text = partial.get("partial", "").strip()
                    if self._check_text(text):
                        print(f"DEBUG: Wake word detected (partial) in '{text}'!")
                        self.rec.Result()
                        return True


