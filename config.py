"""
Application configuration loaded from environment variables.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Paths ────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
AUDIO_DIR = BASE_DIR / "audio_cache"
LOG_DIR = BASE_DIR / "logs"
AUDIO_DIR.mkdir(exist_ok=True)

# ── Gemini / LLM ────────────────────────────────────────────────────────
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
MAX_TOKENS: int = 512  # keep replies short for TTS

# ── Whisper (STT) ───────────────────────────────────────────────────────
WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "base")

# ── Edge-TTS voices ─────────────────────────────────────────────────────
TTS_VOICES: dict[str, str] = {
    "en": os.getenv("TTS_VOICE_EN", "en-IN-NeerjaNeural"),
    "hi": os.getenv("TTS_VOICE_HI", "hi-IN-SwaraNeural"),
    "mr": os.getenv("TTS_VOICE_MR", "mr-IN-AarohiNeural"),
}

# ── Privacy & Logging ───────────────────────────────────────────────────
ENABLE_LOGGING: bool = os.getenv("ENABLE_LOGGING", "false").lower() == "true"
if ENABLE_LOGGING:
    LOG_DIR.mkdir(exist_ok=True)

# ── UI ───────────────────────────────────────────────────────────────────
APP_TITLE = "CareNova AI — Intelligent Health Companion"
DISCLAIMER = (
    "⚠️ **Medical Disclaimer:** I am **CareNova AI**, an intelligent *health information assistant*, "
    "**not a licensed medical doctor**. I cannot diagnose diseases, prescribe medication dosages, "
    "or replace personal medical examinations. In emergencies, call **112** (India) or your local "
    "emergency services immediately. Always seek the advice of a qualified physician."
)

# ── Google Maps clinic search ────────────────────────────────────────────
CLINIC_SEARCH_URL = "https://www.google.com/maps/search/clinic+near+me"
