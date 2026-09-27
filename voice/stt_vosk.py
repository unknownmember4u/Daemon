import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel
from core.config import load_config
from voice.audio_utils import get_native_sample_rate, process_audio_for_whisper
import queue


class SpeechToText:
    def __init__(self):
        cfg = load_config()
        self.device = cfg["audio"].get("input_device")
        self.native_sr = get_native_sample_rate(self.device)
        self.max_seconds = cfg["stt"].get("max_seconds", 10)
        
        print("DEBUG: Loading Whisper STT model...")
        # For full commands, we use beam_size=5 for better accuracy
        self.model = WhisperModel("base.en", device="cpu", compute_type="int8")

        self.ambient_energy = 0
        self.energy_multiplier = 3.0
        self.min_energy = 100
        
        self.q = queue.Queue()

    def _audio_callback(self, indata, frames, time_info, status):
        """This is called for each audio block by sounddevice."""
        if status:
            pass
        self.q.put(bytes(indata))

    def _calibrate_noise(self, duration=0.5):
        # Allow hardware to warm up and stabilize
        print("DEBUG: Warming up audio device...")
        import time
        time.sleep(0.2)
        
        # Empty queue first
        while not self.q.empty():
            try:
                self.q.get_nowait()
            except queue.Empty:
                break
                
        samples = []
        chunk_ms = 50
        chunks_needed = int(duration * 1000 / chunk_ms)
        
        for _ in range(chunks_needed):
            try:
                data = self.q.get(timeout=2.0)
                samples.append(np.frombuffer(data, dtype=np.int16))
            except queue.Empty:
                break
                
        if not samples:
            return self.min_energy
            
        audio = np.concatenate(samples)
        self.ambient_energy = np.sqrt(np.mean(audio.astype(np.float32) ** 2))
        return max(self.ambient_energy * self.energy_multiplier, self.min_energy)

    def listen_once(self) -> str:
        chunk_ms = 50
        chunk_samples = int(self.native_sr * chunk_ms / 1000)
        
        # Clear queue
        while not self.q.empty():
            try:
                self.q.get_nowait()
            except queue.Empty:
                break
                
        print("DEBUG: STT listening for command...")

        with sd.RawInputStream(samplerate=self.native_sr, channels=1,
                               dtype='int16', device=self.device,
                               blocksize=chunk_samples,
                               callback=self._audio_callback):
            
            threshold = self._calibrate_noise()

            audio_frames = []
            pre_buffer = []
            pre_buffer_size = 6

            speech_started = False
            silence_chunks = 0
            max_silence_chunks = int(1.5 * 1000 / chunk_ms)
            max_chunks = int(self.max_seconds * 1000 / chunk_ms)
            max_wait_chunks = int(5.0 * 1000 / chunk_ms)
            waited_chunks = 0

            while True:
                try:
                    data_bytes = self.q.get(timeout=2.0)
                except queue.Empty:
                    print("DEBUG: STT queue timeout")
                    return ""
                    
                data = np.frombuffer(data_bytes, dtype=np.int16)
                energy = np.sqrt(np.mean(data.astype(np.float32) ** 2))

                if not speech_started:
                    pre_buffer.append(data.copy())
                    if len(pre_buffer) > pre_buffer_size:
                        pre_buffer.pop(0)
                    if energy > threshold:
                        speech_started = True
                        audio_frames.extend(pre_buffer)
                        audio_frames.append(data.copy())
                        silence_chunks = 0
                    else:
                        waited_chunks += 1
                        if waited_chunks >= max_wait_chunks:
                            print("DEBUG: STT timed out waiting for speech")
                            return ""
                else:
                    audio_frames.append(data.copy())
                    if energy > threshold:
                        silence_chunks = 0
                    else:
                        silence_chunks += 1
                        if silence_chunks >= max_silence_chunks:
                            break
                    if len(audio_frames) >= max_chunks:
                        break

        if not speech_started or len(audio_frames) < 5:
            return ""

        audio = np.concatenate(audio_frames)
        audio_bytes = audio.tobytes()
        audio_np = process_audio_for_whisper(audio_bytes, self.native_sr)
        
        segments, info = self.model.transcribe(
            audio_np, beam_size=5, language="en",
            vad_filter=True, vad_parameters=dict(min_silence_duration_ms=500)
        )
        text = "".join(segment.text for segment in segments).strip()
        
        # Post-process common homophone mistakes
        text_lower = text.lower()
        if "demon" in text_lower or "damon" in text_lower:
            # Simple replace just for aesthetic display
            text = text.replace("demon", "daemon").replace("Demon", "Daemon")
            text = text.replace("damon", "daemon").replace("Damon", "Daemon")
            text = text.replace("daymon", "daemon").replace("Daymon", "Daemon")
        
        print(f"DEBUG: STT recognized: '{text}'")
        return text
