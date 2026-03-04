import os
import time
import numpy as np
from faster_whisper import WhisperModel
from core.i18n import LANG_CODE

HALLUCINATION_KEYWORDS = ["ご視聴", "チャンネル登録", "ありがとうございました", "字幕:"]
HALLUCINATION_MAX_LEN = 15
SAMPLE_RATE = 16000

class WhisperEngine:
    def __init__(self):
        self.model = None

    @staticmethod
    def is_model_cached(model_name: str) -> bool:
        """モデルが既にHuggingFaceキャッシュにあるか確認。"""
        cache_dir = os.path.join(os.path.expanduser("~"), ".cache", "huggingface", "hub")
        patterns = [
            f"models--Systran--faster-whisper-{model_name}",
            f"models--guillaumekln--faster-whisper-{model_name}",
            f"models--mobiuslabsgmbh--faster-whisper-{model_name}",
        ]
        return any(os.path.exists(os.path.join(cache_dir, p)) for p in patterns)

    def load_model(self, model_name: str, cpu_threads: int):
        self.model = WhisperModel(
            model_name, device="cpu", compute_type="int8", cpu_threads=cpu_threads,
        )

    def transcribe(self, audio: np.ndarray, initial_prompt: str) -> str:
        if not self.model:
            return ""
        t_start = time.time()
        whisper_lang = {"ja": "ja", "en": "en", "ko": "ko", "zh": "zh"}.get(LANG_CODE, "en")
        segments, _ = self.model.transcribe(
            audio, language=whisper_lang, beam_size=1, best_of=1, temperature=0,
            initial_prompt=initial_prompt, without_timestamps=True,
            condition_on_previous_text=False, vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=300, speech_pad_ms=200),
        )
        text = "".join(s.text for s in segments).strip()
        elapsed = time.time() - t_start
        audio_sec = len(audio) / SAMPLE_RATE
        print(f"[計測] 音声: {audio_sec:.1f}秒 → 処理: {elapsed:.2f}秒 (速度比: {audio_sec / elapsed:.1f}x)")
        return text

    @staticmethod
    def filter_noise(text: str, noise_cancel_enabled: bool) -> str:
        if not text or not noise_cancel_enabled:
            return text
        if any(kw in text for kw in HALLUCINATION_KEYWORDS) and len(text) < HALLUCINATION_MAX_LEN:
            return ""
        return text
