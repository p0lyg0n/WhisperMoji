import sounddevice as sd
import numpy as np

SAMPLE_RATE = 16000

class AudioManager:
    """マイクの管理・録音デバイス操作"""
    
    @staticmethod
    def get_microphones() -> tuple[list[str], dict[str, int]]:
        mic_list = []
        mic_id_map = {}
        try:
            for i, dev in enumerate(sd.query_devices()):
                if dev["max_input_channels"] > 0:
                    label = f"[{i}] {dev['name']}"
                    mic_list.append(label)
                    mic_id_map[label] = i
        except Exception:
            pass
        return mic_list, mic_id_map

    @staticmethod
    def get_default_microphone(mic_id_map: dict[str, int]) -> str:
        try:
            default_id = sd.default.device[0]
            for label, dev_id in mic_id_map.items():
                if dev_id == default_id:
                    return label
        except Exception:
            pass
        return ""

    @staticmethod
    def prepare_audio_buffer(audio_buffer: list, gain: float) -> np.ndarray:
        if not audio_buffer:
            return np.array([], dtype=np.float32)
        audio = np.concatenate(audio_buffer).flatten().astype(np.float32) * gain
        max_val = np.abs(audio).max()
        if max_val > 0:
            audio = audio / max_val * 0.9
        return audio
