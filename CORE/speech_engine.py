"""
ECHOHANDS - Speech Engine
Bilingual (English & Hindi) speech synthesis metadata generator,
phonetic transliterations, Web Speech API orchestrator, and optional offline fallback.
"""

from typing import Dict, Any, Optional
import io
import base64
from CORE.sign_knowledge import get_sign_info

class SpeechEngine:
    def __init__(self):
        # Voice configurations for browser Web Speech API
        self.supported_locales = {
            "en-IN": {
                "name": "Indian English",
                "lang": "en-IN",
                "default_rate": 0.95,
                "default_pitch": 1.0,
                "default_volume": 1.0
            },
            "hi-IN": {
                "name": "Hindi (India)",
                "lang": "hi-IN",
                "default_rate": 0.90,
                "default_pitch": 1.0,
                "default_volume": 1.0
            }
        }

    def generate_tts_metadata(
        self,
        english_sentence: str,
        hindi_sentence: str,
        preferred_lang: str = "en-IN"
    ) -> Dict[str, Any]:
        """
        Generate full browser Web Speech API configuration payload
        along with phonetic transliterations and speech parameters.
        """
        norm_lang = preferred_lang if preferred_lang in self.supported_locales else "en-IN"
        config = self.supported_locales[norm_lang]

        target_text = hindi_sentence if "hi" in norm_lang else english_sentence
        alt_text = english_sentence if "hi" in norm_lang else hindi_sentence

        # Compute phonetic hints
        phonetic_hint = self.generate_phonetic_hint(english_sentence, hindi_sentence, norm_lang)

        return {
            "primary": {
                "text": target_text,
                "lang": norm_lang,
                "rate": config["default_rate"],
                "pitch": config["default_pitch"],
                "volume": config["default_volume"],
                "phonetic_hint": phonetic_hint
            },
            "secondary": {
                "text": alt_text,
                "lang": "hi-IN" if norm_lang == "en-IN" else "en-IN",
                "rate": 0.90 if norm_lang == "en-IN" else 0.95,
                "pitch": 1.0,
                "volume": 1.0
            },
            "english_sentence": english_sentence,
            "hindi_sentence": hindi_sentence,
            "waveform_pattern": self._generate_simulated_waveform(target_text)
        }

    def generate_phonetic_hint(self, english_text: str, hindi_text: str, lang: str) -> str:
        """Extract or compose phonetic pronunciation hints."""
        if "hi" in lang.lower():
            words = english_text.replace(".", "").replace("?", "").replace("!", "").split()
            translits = []
            for w in words:
                info = get_sign_info(w)
                if info and "translit" in info:
                    translits.append(info["translit"])
                else:
                    translits.append(w)
            if translits:
                return " ".join(translits)
            return hindi_text

        words = english_text.replace(".", "").replace("?", "").replace("!", "").split()
        phonetics = []
        for w in words:
            info = get_sign_info(w)
            if info and "phonetic" in info:
                phonetics.append(info["phonetic"])
            else:
                phonetics.append(w.lower())
        return " - ".join(phonetics) if phonetics else english_text

    def _generate_simulated_waveform(self, text: str) -> list[float]:
        """
        Generate a normalized simulated 32-bar envelope for audio visualizer
        fallback in case Web Audio API media stream is muted.
        """
        import math
        seed = sum(ord(c) for c in text) if text else 42
        bars = []
        for i in range(32):
            val = abs(math.sin((i + seed % 17) * 0.45) * math.cos(i * 0.3)) * 0.85 + 0.15
            bars.append(round(min(1.0, max(0.1, val)), 3))
        return bars

    def synthesize_offline_audio(self, text: str, lang: str = "en") -> Optional[str]:
        """
        Optional server-side offline TTS rendering using gTTS.
        Returns base64 data URI if available.
        """
        try:
            from gtts import gTTS
            # Map locales
            gtts_lang = "hi" if "hi" in lang.lower() else "en"
            tts = gTTS(text=text, lang=gtts_lang, slow=False)
            fp = io.BytesIO()
            tts.write_to_fp(fp)
            fp.seek(0)
            encoded = base64.b64encode(fp.read()).decode("utf-8")
            return f"data:audio/mp3;base64,{encoded}"
        except Exception:
            # If network or gTTS fails, return None (browser will handle via native Web Speech API)
            return None
