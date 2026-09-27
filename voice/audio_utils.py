import numpy as np
import sounddevice as sd


def get_native_sample_rate(device=None) -> int:
    """Get the native sample rate of the input device."""
    try:
        device_info = sd.query_devices(device, kind='input')
        rate = int(device_info.get('default_samplerate', 44100))
        return rate if rate > 0 else 44100
    except Exception:
        return 44100


def process_audio_for_whisper(audio_bytes: bytes, native_sr: int) -> np.ndarray:
    """Convert raw int16 bytes to 16kHz float32 numpy array for faster-whisper."""
    samples = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
    
    # Simple linear interpolation for resampling to 16000 Hz if needed
    if native_sr != 16000:
        orig_len = len(samples)
        target_len = int(orig_len * 16000 / native_sr)
        orig_indices = np.linspace(0, orig_len - 1, orig_len)
        target_indices = np.linspace(0, orig_len - 1, target_len)
        samples = np.interp(target_indices, orig_indices, samples).astype(np.float32)
        
    return samples
