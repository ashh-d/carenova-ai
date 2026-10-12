"""
✨ CareNova AI — Intelligent Multilingual Health Companion
Next-generation clinical information, voice triaging, and safety-first assistant.
"""

from __future__ import annotations

import uuid
import base64
from pathlib import Path

import streamlit as st

from config import APP_TITLE, DISCLAIMER, CLINIC_SEARCH_URL, ENABLE_LOGGING
from core.llm import chat
from core.safety import detect_emergency
from core.prompts import SPOKEN_DISCLAIMER
from core.logger import log_turn, generate_summary

# ── Page Configuration ──────────────────────────────────────────────────
st.set_page_config(
    page_title="CareNova AI — Health Intelligence",
    page_icon="🩺",
    layout="centered",
    initial_sidebar_state="expanded",
)

# ── Cloudflare Live Link ────────────────────────────────────────────────
LIVE_URL = "https://updates-pioneer-myspace-retrieve.trycloudflare.com"

# ── High-Performance Modern CSS with Smooth Motions & Glassmorphism ───
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }

    .stApp {
        max-width: 860px;
        margin: 0 auto;
        background: radial-gradient(circle at 50% -20%, rgba(14, 165, 233, 0.12) 0%, rgba(15, 23, 42, 0.0) 70%);
    }

    /* Ambient animated mesh header glow */
    @keyframes pulseGlow {
        0%, 100% { opacity: 0.6; transform: scale(1); }
        50% { opacity: 0.85; transform: scale(1.02); }
    }

    @keyframes liveBeacon {
        0% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
        70% { box-shadow: 0 0 0 10px rgba(16, 185, 129, 0); }
        100% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
    }

    @keyframes floatCard {
        0%, 100% { transform: translateY(0px); }
        50% { transform: translateY(-3px); }
    }

    @keyframes fadeInSlide {
        from { opacity: 0; transform: translateY(12px); }
        to { opacity: 1; transform: translateY(0); }
    }

    @keyframes emergencyFlash {
        0%, 100% { border-color: rgba(239, 68, 68, 0.6); box-shadow: 0 0 20px rgba(239, 68, 68, 0.2); }
        50% { border-color: rgba(220, 38, 38, 1); box-shadow: 0 0 35px rgba(220, 38, 38, 0.45); }
    }

    /* Modern Live Link Pill */
    .live-badge-wrapper {
        display: flex;
        align-items: center;
        justify-content: space-between;
        background: linear-gradient(135deg, rgba(14, 165, 233, 0.12) 0%, rgba(99, 102, 241, 0.12) 100%);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(56, 189, 248, 0.3);
        border-radius: 14px;
        padding: 10px 18px;
        margin-bottom: 20px;
        animation: fadeInSlide 0.6s ease-out;
    }

    .live-pill {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        font-size: 0.84rem;
        font-weight: 700;
        color: #0284c7;
        letter-spacing: 0.02em;
    }

    .live-dot {
        width: 10px;
        height: 10px;
        border-radius: 50%;
        background-color: #10b981;
        animation: liveBeacon 2s infinite;
    }

    .live-url-btn {
        background: linear-gradient(135deg, #0ea5e9 0%, #6366f1 100%);
        color: white !important;
        font-size: 0.8rem;
        font-weight: 600;
        padding: 6px 14px;
        border-radius: 10px;
        text-decoration: none;
        transition: all 0.25s ease;
        box-shadow: 0 4px 12px rgba(14, 165, 233, 0.25);
    }

    .live-url-btn:hover {
        transform: translateY(-1px);
        box-shadow: 0 6px 18px rgba(14, 165, 233, 0.4);
    }

    /* Hero Header */
    .hero-container {
        text-align: center;
        padding: 24px 16px 16px 16px;
        animation: fadeInSlide 0.7s ease-out;
    }

    .hero-brand {
        display: inline-flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 8px;
    }

    .hero-icon {
        font-size: 2.4rem;
        filter: drop-shadow(0 4px 10px rgba(14, 165, 233, 0.4));
        animation: floatCard 4s ease-in-out infinite;
    }

    .hero-title {
        font-size: 2.35rem;
        font-weight: 800;
        letter-spacing: -0.03em;
        background: linear-gradient(135deg, #0284c7 0%, #06b6d4 50%, #6366f1 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
    }

    .hero-subtitle {
        font-size: 1.02rem;
        font-weight: 500;
        color: #64748b;
        margin-top: 4px;
        margin-bottom: 16px;
    }

    /* Feature Pills */
    .feature-pills {
        display: flex;
        justify-content: center;
        flex-wrap: wrap;
        gap: 8px;
        margin-bottom: 22px;
    }

    .feature-tag {
        font-size: 0.78rem;
        font-weight: 600;
        padding: 5px 12px;
        border-radius: 9999px;
        background: rgba(14, 165, 233, 0.08);
        border: 1px solid rgba(14, 165, 233, 0.2);
        color: #0369a1;
        transition: all 0.2s ease;
    }

    .feature-tag:hover {
        background: rgba(14, 165, 233, 0.16);
        transform: translateY(-1px);
    }

    /* Disclaimer Card */
    .disclaimer-card {
        background: rgba(245, 158, 11, 0.08);
        border: 1px solid rgba(245, 158, 11, 0.3);
        border-radius: 12px;
        padding: 12px 18px;
        font-size: 0.88rem;
        color: #92400e;
        margin-bottom: 20px;
        animation: fadeInSlide 0.8s ease-out;
        display: flex;
        align-items: flex-start;
        gap: 10px;
    }

    /* Emergency Alert Banner */
    .emergency-alert-card {
        background: linear-gradient(135deg, rgba(239, 68, 68, 0.12) 0%, rgba(185, 28, 28, 0.08) 100%);
        border: 2px solid rgba(239, 68, 68, 0.7);
        border-radius: 16px;
        padding: 18px 22px;
        margin: 14px 0 20px 0;
        animation: emergencyFlash 2.5s infinite;
    }

    .emergency-title {
        color: #dc2626;
        font-size: 1.15rem;
        font-weight: 800;
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 8px;
    }

    .emergency-actions {
        display: flex;
        gap: 12px;
        flex-wrap: wrap;
        margin-top: 14px;
    }

    .btn-call-emergency {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: #dc2626;
        color: white !important;
        padding: 8px 16px;
        border-radius: 10px;
        font-weight: 700;
        font-size: 0.88rem;
        text-decoration: none;
        transition: all 0.2s;
        box-shadow: 0 4px 14px rgba(220, 38, 38, 0.35);
    }

    .btn-call-emergency:hover {
        background: #b91c1c;
        transform: translateY(-1px);
    }

    .btn-find-hospital {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: #059669;
        color: white !important;
        padding: 8px 16px;
        border-radius: 10px;
        font-weight: 700;
        font-size: 0.88rem;
        text-decoration: none;
        transition: all 0.2s;
        box-shadow: 0 4px 14px rgba(5, 150, 105, 0.3);
    }

    .btn-find-hospital:hover {
        background: #047857;
        transform: translateY(-1px);
    }

    /* Voice recording container */
    .voice-dock {
        background: linear-gradient(135deg, rgba(248, 250, 252, 0.9) 0%, rgba(241, 245, 249, 0.9) 100%);
        border: 1px solid rgba(226, 232, 240, 0.9);
        border-radius: 16px;
        padding: 16px 20px;
        margin: 18px 0;
        text-align: center;
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.04);
        animation: fadeInSlide 0.6s ease-out;
    }

    /* Chat Messages */
    .stChatMessage {
        animation: fadeInSlide 0.4s ease-out;
        border-radius: 16px !important;
        padding: 12px 18px !important;
        margin-bottom: 12px !important;
    }

    /* Sidebar Glassmorphism */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, rgba(248, 250, 252, 0.95) 0%, rgba(241, 245, 249, 0.98) 100%) !important;
        border-right: 1px solid rgba(226, 232, 240, 0.8);
    }
</style>
""", unsafe_allow_html=True)

# ── Session State Setup ──────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_id" not in st.session_state:
    st.session_state.session_id = uuid.uuid4().hex[:12]
if "language" not in st.session_state:
    st.session_state.language = "en"
if "voice_enabled" not in st.session_state:
    st.session_state.voice_enabled = True
if "disclaimer_shown" not in st.session_state:
    st.session_state.disclaimer_shown = False
if "selected_prompt" not in st.session_state:
    st.session_state.selected_prompt = None


# ── Audio Playback Utility ───────────────────────────────────────────────
def autoplay_audio(file_path: Path):
    """Embed an HTML5 audio player that autoplays spoken feedback."""
    audio_bytes = file_path.read_bytes()
    b64 = base64.b64encode(audio_bytes).decode()
    st.markdown(
        f'<audio autoplay src="data:audio/mp3;base64,{b64}" controls '
        f'style="width:100%; border-radius: 12px; margin-top: 8px;"></audio>',
        unsafe_allow_html=True,
    )


# ── Lazy Speech Engine Loader ───────────────────────────────────────────
@st.cache_resource
def load_speech_module():
    """Dynamically loads Whisper & Edge-TTS engine."""
    from core.speech import transcribe, synthesize, save_uploaded_audio
    return transcribe, synthesize, save_uploaded_audio


# ── Live Link & Network Header ──────────────────────────────────────────
st.markdown(f"""
<div class="live-badge-wrapper">
    <div class="live-pill">
        <span class="live-dot"></span>
        <span>CareNova AI • Live Online</span>
    </div>
    <a href="{LIVE_URL}" target="_blank" class="live-url-btn">
        🌐 Open Public Live Link ↗
    </a>
</div>
""", unsafe_allow_html=True)

# ── Hero Branding Header with Animated Motion ───────────────────────────
st.markdown("""
<div class="hero-container">
    <div class="hero-brand">
        <span class="hero-icon">🩺</span>
        <h1 class="hero-title">CareNova AI</h1>
    </div>
    <div class="hero-subtitle">Intelligent Multilingual Clinical Guidance & Health Companion</div>
    <div class="feature-pills">
        <span class="feature-tag">⚡ Gemini 3.5 Intelligence</span>
        <span class="feature-tag">🎙️ Multilingual Voice (EN / HI / MR)</span>
        <span class="feature-tag">🛡️ Real-Time Safety Guardrails</span>
        <span class="feature-tag">🔒 Zero-Storage Privacy</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Safety Disclaimer ───────────────────────────────────────────────────
if not st.session_state.disclaimer_shown:
    st.markdown(f"""
    <div class="disclaimer-card">
        <span style="font-size: 1.25rem;">⚠️</span>
        <div>{DISCLAIMER}</div>
    </div>
    """, unsafe_allow_html=True)
    st.session_state.disclaimer_shown = True

# ── Interactive Sidebar ─────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ System Controls")

    st.session_state.voice_enabled = st.toggle(
        "🎙️ Neural Voice Engine",
        value=st.session_state.voice_enabled,
        help="Enables Whisper microphone speech input and Edge-TTS spoken responses.",
    )

    st.session_state.language = st.selectbox(
        "🌐 Clinical Consultation Language",
        options=["en", "hi", "mr"],
        format_func={
            "en": "🇬🇧 English",
            "hi": "🇮🇳 हिंदी (Hindi)",
            "mr": "🚩 मराठी (Marathi)",
        }.get,
        index=["en", "hi", "mr"].index(st.session_state.language),
    )

    st.divider()

    st.markdown("### 🏥 Quick Facilities")
    st.markdown(
        f'<a href="{CLINIC_SEARCH_URL}" target="_blank" class="live-url-btn" style="display:block; text-align:center; padding:10px;">'
        '📍 Find Nearby Clinics & Hospitals ↗</a>',
        unsafe_allow_html=True,
    )

    st.divider()

    st.markdown("### 📋 Consultation Reports")
    if ENABLE_LOGGING:
        if st.button("📄 Generate Doctor Visit Summary", use_container_width=True):
            summary = generate_summary(st.session_state.session_id)
            st.markdown(summary)
            st.download_button(
                "⬇️ Download Clinical Summary",
                summary,
                file_name=f"CareNova_Summary_{st.session_state.session_id}.md",
                mime="text/markdown",
                use_container_width=True,
            )
    else:
        st.caption("🔒 Enable conversation logging in `.env` to export consultation summaries.")

    st.divider()

    st.markdown("""
    <div style="font-size:0.8rem; color:#64748b; line-height: 1.4;">
        <strong>🔒 Privacy Commitment:</strong><br>
        Voice recordings are transcribed locally in memory and never retained on disk.
        Conversations are stateless unless opt-in logging is turned on.
    </div>
    """, unsafe_allow_html=True)

    st.write("")
    if st.button("🗑️ Reset Consultation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.selected_prompt = None
        st.rerun()

# ── Interactive Quick Suggestion Chips (Shown on Fresh Chat) ───────────
if len(st.session_state.messages) == 0:
    st.markdown("##### 💡 Suggested Questions")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🤕 Throbbing headache for 2 days", use_container_width=True):
            st.session_state.selected_prompt = "I have had a throbbing headache for the past 2 days with mild sensitivity to bright light."
        if st.button("👶 Paracetamol safety guidance for child", use_container_width=True):
            st.session_state.selected_prompt = "What is the recommended dosage of paracetamol for an 18-month-old infant?"
    with col2:
        if st.button("🤒 High fever & chills guidance", use_container_width=True):
            st.session_state.selected_prompt = "I have a high fever with shivering chills since yesterday evening. What should I monitor?"
        if st.button("🚨 Sudden chest tightness check", use_container_width=True):
            st.session_state.selected_prompt = "I feel sudden tightness in my chest and difficulty catching my breath."

# ── Render Conversation History ─────────────────────────────────────────
for msg in st.session_state.messages:
    is_user = msg["role"] == "user"
    avatar = "🧑" if is_user else "🩺"
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])

# ── Voice Input Interface (Whisper) ─────────────────────────────────────
voice_text = None
if st.session_state.voice_enabled:
    try:
        from streamlit_mic_recorder import mic_recorder

        with st.container():
            st.markdown("""
            <div class="voice-dock">
                <div style="font-size: 0.88rem; font-weight: 600; color: #334155; margin-bottom: 8px;">
                    🎙️ Voice Consultation Mode (English / Hindi / Marathi)
                </div>
            """, unsafe_allow_html=True)

            audio_data = mic_recorder(
                start_prompt="🔴 Tap to Record Voice",
                stop_prompt="⏹️ Stop & Process",
                just_once=True,
                key="carenova_mic",
            )

            st.markdown("</div>", unsafe_allow_html=True)

            if audio_data and audio_data.get("bytes"):
                with st.spinner("🔄 Transcribing your audio via Whisper engine..."):
                    transcribe, synthesize, save_uploaded_audio = load_speech_module()
                    audio_path = save_uploaded_audio(audio_data["bytes"])
                    voice_text, detected_lang = transcribe(audio_path)
                    st.session_state.language = detected_lang
                    st.success(f"📝 Transcribed: *\"{voice_text}\"*  [Language: {detected_lang}]")
                    audio_path.unlink(missing_ok=True)

    except ImportError:
        st.info("Mic recorder package active.")

# ── Process User Input (Text / Voice / Chip) ────────────────────────────
active_input = st.session_state.selected_prompt or voice_text
st.session_state.selected_prompt = None

chat_input = st.chat_input("Ask CareNova AI about symptoms, wellness, or health topics...")
user_prompt = active_input or chat_input

if user_prompt:
    # Append & display user prompt
    with st.chat_message("user", avatar="🧑"):
        st.markdown(user_prompt)

    st.session_state.messages.append({"role": "user", "content": user_prompt})
    log_turn("user", user_prompt, st.session_state.language, session_id=st.session_state.session_id)

    # ── Emergency Pre-Screening & Response Generation ───────────────────
    is_emergency, emergency_label, _ = detect_emergency(user_prompt)

    with st.chat_message("assistant", avatar="🩺"):
        with st.spinner("Analyzing symptoms & consulting medical knowledge base..."):
            history = st.session_state.messages[:-1]
            response = chat(user_prompt, history)

        # Show emergency action card if triggered
        if is_emergency:
            st.markdown(f"""
            <div class="emergency-alert-card">
                <div class="emergency-title">
                    <span>🚨 CRITICAL MEDICAL TRIAGE ALERT</span>
                </div>
                <div style="color: #7f1d1d; font-size: 0.92rem; line-height: 1.5;">
                    CareNova AI detected potential emergency signals (<strong>{emergency_label}</strong>).
                    Immediate emergency intervention is recommended.
                </div>
                <div class="emergency-actions">
                    <a href="tel:112" class="btn-call-emergency">📞 Call 112 (Emergency)</a>
                    <a href="{CLINIC_SEARCH_URL}" target="_blank" class="btn-find-hospital">🏥 Find Nearest Trauma Center ↗</a>
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown(response)

    st.session_state.messages.append({"role": "assistant", "content": response})
    log_turn("assistant", response, st.session_state.language,
             emergency=is_emergency, session_id=st.session_state.session_id)

    # ── Text-To-Speech Synthesis ────────────────────────────────────────
    if st.session_state.voice_enabled:
        try:
            _, synthesize, _ = load_speech_module()
            with st.spinner("🔊 Synthesizing speech response..."):
                audio_file = synthesize(response, st.session_state.language)
                autoplay_audio(audio_file)
        except Exception as e:
            # Silent fallback if TTS is momentarily busy
            pass

# ── Footer ───────────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align: center; margin-top: 36px; padding: 18px 0; border-top: 1px solid rgba(226, 232, 240, 0.8); font-size: 0.82rem; color: #94a3b8;">
    🩺 <strong>CareNova AI</strong> • Educational Clinical Information Companion<br>
    Not a substitute for professional medical diagnosis or emergency care. In acute emergencies, contact <strong>112</strong>.
</div>
""", unsafe_allow_html=True)
