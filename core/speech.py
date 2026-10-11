"""
Speech-to-text (Whisper) and text-to-speech (Edge-TTS) integration.

- STT: OpenAI Whisper runs locally, auto-detects language.
- TTS: Edge-TTS provides high-quality neural voices for English, Hindi, Marathi.
"""

from __future__ import annotations

import asyncio
import hashlib
import tempfile
from pathlib import Path
from typing import Optional

import whisper
import edge_tts

from config import WHISPER_MODEL, TTS_VOICES, AUDIO_DIR


# ── Whisper (Speech-to-Text) ────────────────────────────────────────────

_whisper_model: Optional[whisper.Whisper] = None


def _load_whisper():
    global _whisper_model
    if _whisper_model is None:
        _whisper_model = whisper.load_model(WHISPER_MODEL)
    return _whisper_model


def transcribe(audio_path: str | Path) -> tuple[str, str]:
    """Transcribe an audio file using Whisper.

    Args:
        audio_path: Path to the audio file (WAV, MP3, etc.)

    Returns:
        (transcribed_text, detected_language_code)
        e.g. ("मुझे सिरदर्द है", "hi")
    """
    model = _load_whisper()
    result = model.transcribe(
        str(audio_path),
        fp16=False,  # safer on CPU
    )
    text: str = result["text"].strip()
    lang: str = result.get("language", "en")
    return text, lang


# ── Edge-TTS (Text-to-Speech) ───────────────────────────────────────────

def _get_voice(lang: str) -> str:
    """Map a language code to the configured Edge-TTS voice."""
    # Normalize: "hi" -> "hi", "hindi" -> "hi", "marathi" -> "mr"
    lang = lang.lower()[:2]
    return TTS_VOICES.get(lang, TTS_VOICES["en"])


async def _synthesize_async(text: str, lang: str, output_path: Path) -> None:
    """Async helper to run Edge-TTS synthesis."""
    voice = _get_voice(lang)
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(output_path))


def synthesize(text: str, lang: str = "en") -> Path:
    """Convert text to speech using Edge-TTS.

    Uses a content-based cache: identical text+lang combinations reuse
    the same audio file instead of re-synthesizing.

    Args:
        text: The text to speak.
        lang: Language code ("en", "hi", "mr").

    Returns:
        Path to the generated MP3 file.
    """
    # Cache key based on text + language
    cache_key = hashlib.md5(f"{lang}:{text}".encode()).hexdigest()
    output_path = AUDIO_DIR / f"{cache_key}.mp3"

    if not output_path.exists():
        asyncio.run(_synthesize_async(text, lang, output_path))

    return output_path


def save_uploaded_audio(audio_bytes: bytes) -> Path:
    """Save uploaded/recorded audio bytes to a temp file for Whisper.

    Args:
        audio_bytes: Raw audio data from the mic recorder widget.

    Returns:
        Path to the saved audio file.
    """
    tmp = tempfile.NamedTemporaryFile(
        suffix=".wav", delete=False, dir=str(AUDIO_DIR)
    )
    tmp.write(audio_bytes)
    tmp.close()
    return Path(tmp.name)
