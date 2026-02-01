import subprocess

class EspeakTTS:
    def speak(self, text: str):
        if not text:
            return
        subprocess.run(
            ["espeak-ng", text],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
