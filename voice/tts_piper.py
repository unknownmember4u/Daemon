import subprocess
from core.config import load_config

class PiperTTS:
    def __init__(self):
        cfg = load_config()
        self.model = cfg["tts"]["piper_model"]

    def speak(self, text: str):
        if not text:
            return

        piper = subprocess.Popen(
            [
                "env",
                "-u", "VIRTUAL_ENV",
                "-u", "PYTHONPATH",
                "piper",
                self.model,
                "-o", "/dev/stdout",
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )

        pw = subprocess.Popen(
            ["pw-play", "-"],
            stdin=piper.stdout,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        try:
            piper.stdin.write(text.encode("utf-8"))
            piper.stdin.close()
            pw.wait()
        except BrokenPipeError:
            pass
