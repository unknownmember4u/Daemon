import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel
from core.config import load_config
from voice.audio_utils import get_native_sample_rate, process_audio_for_whisper
import queue
import time


class WakeWordListener:
    def __init__(self):
        cfg = load_config()
        self.device = cfg["audio"].get("input_device")
        self.native_sr = get_native_sample_rate(self.device)
        self.wake_word = cfg["assistant"]["wake_word"].lower()
        
        print("DEBUG: Loading Whisper wake word model...")
        self.model = WhisperModel("base.en", device="cpu", compute_type="int8")

        self.wake_variants = {
            "daemon", "demon", "damon", "daymon", "diamond",
            "damen", "demons", "demon's", "timon", "demand",
        }
        self.prefix_words = {"hey", "hi", "hello", "he", "a", "hay", "they"}

        self.ambient_energy = 0
        self.energy_multiplier = 3.0
        self.min_energy = 100
        
        self.q = queue.Queue()

    def _audio_callback(self, indata, frames, time_info, status):
        """This is called for each audio block by sounddevice."""
        if status:
            pass
        self.q.put(bytes(indata))

    def _calibrate_noise(self, duration=1.0):
        # Allow hardware to warm up and stabilize
        print("DEBUG: Warming up audio device...")
        time.sleep(1.0)
        
        # Empty queue of warmup junk
        while not self.q.empty():
            try:
                self.q.get_nowait()
            except queue.Empty:
                break
            
        print("DEBUG: Calibrating ambient noise...")
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
        threshold = max(self.ambient_energy * self.energy_multiplier, self.min_energy)
        print(f"DEBUG: Ambient noise: {self.ambient_energy:.0f}, speech threshold: {threshold:.0f}")
        return threshold

    def _record_speech(self, threshold, max_wait=10.0, max_speech=3.0,
                       silence_duration=0.5, pre_speech_buffer=0.3):
        chunk_ms = 50
        pre_buffer_size = int(pre_speech_buffer * 1000 / chunk_ms)
        max_silence_chunks = int(silence_duration * 1000 / chunk_ms)
        max_speech_chunks = int(max_speech * 1000 / chunk_ms)
        max_wait_chunks = int(max_wait * 1000 / chunk_ms)

        audio_frames = []
        pre_buffer = []
        speech_started = False
        silence_chunks = 0
        waited_chunks = 0
        max_energy = 0

        while True:
            try:
                data_bytes = self.q.get(timeout=2.0)
            except queue.Empty:
                print("DEBUG: Audio queue timeout")
                return None
                
            data = np.frombuffer(data_bytes, dtype=np.int16)
            energy = np.sqrt(np.mean(data.astype(np.float32) ** 2))
            if energy > max_energy:
                max_energy = energy

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
                        return None
            else:
                audio_frames.append(data.copy())
                if energy > threshold:
                    silence_chunks = 0
                else:
                    silence_chunks += 1
                    if silence_chunks >= max_silence_chunks:
                        break

                if len(audio_frames) >= max_speech_chunks:
                    break

        if len(audio_frames) < 5:
            return None

        audio = np.concatenate(audio_frames)
        print(f"DEBUG: Speech block finished. Max energy: {max_energy:.0f}")
        return audio.tobytes()

    def _is_wake_word(self, text: str) -> bool:
        text = text.lower().strip()
        if not text:
            return False
        if self.wake_word in text:
            return True

        words = text.split()
        has_prefix = any(w in self.prefix_words for w in words)
        has_variant = any(v in words for v in self.wake_variants)
        has_variant_sub = any(v in text for v in self.wake_variants)

        if has_prefix and (has_variant or has_variant_sub):
            return True
        return False

    def wait(self):
        chunk_ms = 50
        chunk_samples = int(self.native_sr * chunk_ms / 1000)
        
        # Clear queue
        while not self.q.empty():
            try:
                self.q.get_nowait()
            except queue.Empty:
                break
                
        print(f"DEBUG: Listening for wake word '{self.wake_word}'...")
        
        # Open stream ONCE and keep it open
        with sd.RawInputStream(samplerate=self.native_sr, channels=1,
                               dtype='int16', device=self.device,
                               blocksize=chunk_samples,
                               callback=self._audio_callback):
            
            threshold = self._calibrate_noise()

            while True:
                print("DEBUG: Waiting for speech...")
                audio_bytes = self._record_speech(threshold)
                if audio_bytes is None:
                    print("DEBUG: _record_speech returned None")
                    continue

                print(f"DEBUG: Recorded {len(audio_bytes)} bytes of audio. Transcribing...")
                audio_np = process_audio_for_whisper(audio_bytes, self.native_sr)
                segments, info = self.model.transcribe(
                    audio_np, beam_size=1, language="en", condition_on_previous_text=False,
                    vad_filter=True, vad_parameters=dict(min_silence_duration_ms=500)
                )
                
                text = "".join(segment.text for segment in segments).strip()
                print(f"DEBUG: Transcribed text: '{text}'")
                if text:
                    print(f"DEBUG: WakeWord heard: '{text}'")

                    if self._is_wake_word(text):
                        print(f"DEBUG: ✓ Wake word DETECTED in '{text}'!")
                        return True
