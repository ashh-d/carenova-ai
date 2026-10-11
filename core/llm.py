"""
LLM integration — Google Gemini API via the google-genai SDK.

Supports streaming for lower perceived latency (the TTS pipeline can start
speaking as soon as the first sentence is complete).
"""

from __future__ import annotations

from typing import Generator

from google import genai
from google.genai import types

from config import GEMINI_API_KEY, GEMINI_MODEL, MAX_TOKENS
from core.prompts import SYSTEM_PROMPT
from core.safety import detect_emergency, audit_response


def _get_client() -> genai.Client:
    if not GEMINI_API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. "
            "Copy .env.example to .env and add your key."
        )
    return genai.Client(api_key=GEMINI_API_KEY)


def chat(
    user_message: str,
    history: list[dict[str, str]],
) -> str:
    """Send a message and return the full assistant response.

    Args:
        user_message: The latest user input.
        history: List of {"role": "user"|"assistant", "content": "..."} dicts.

    Returns:
        The assistant's reply (already safety-audited).
    """
    # ── Phase 3: Pre-LLM emergency check ────────────────────────────
    is_emergency, label, emergency_response = detect_emergency(user_message)
    if is_emergency:
        return emergency_response

    # ── Build message list for Gemini ────────────────────────────────
    # Gemini uses "user" and "model" roles (not "assistant")
    contents: list[types.Content] = []
    for msg in history:
        role = "model" if msg["role"] == "assistant" else "user"
        contents.append(types.Content(
            role=role,
            parts=[types.Part.from_text(text=msg["content"])],
        ))
    # Add the latest user message
    contents.append(types.Content(
        role="user",
        parts=[types.Part.from_text(text=user_message)],
    ))

    client = _get_client()
    candidate_models = list(dict.fromkeys([GEMINI_MODEL, "gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-3.8-flash"]))

    response = None
    last_err = None
    for model_name in candidate_models:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    max_output_tokens=MAX_TOKENS,
                    temperature=0.7,
                ),
            )
            break
        except Exception as e:
            last_err = e
            continue

    if response is None:
        raise last_err or RuntimeError("All Gemini candidate models failed.")

    text = response.text or ""

    # ── Phase 3: Post-LLM guardrail audit ────────────────────────────
    text = audit_response(text)
    return text


def chat_stream(
    user_message: str,
    history: list[dict[str, str]],
) -> Generator[str, None, None]:
    """Stream the assistant response sentence-by-sentence.

    Yields complete sentences so the TTS pipeline can start speaking
    before the full response is ready.
    """
    # ── Emergency short-circuit ──────────────────────────────────────
    is_emergency, _, emergency_response = detect_emergency(user_message)
    if is_emergency:
        yield emergency_response
        return

    # ── Build message list for Gemini ────────────────────────────────
    contents: list[types.Content] = []
    for msg in history:
        role = "model" if msg["role"] == "assistant" else "user"
        contents.append(types.Content(
            role=role,
            parts=[types.Part.from_text(text=msg["content"])],
        ))
    contents.append(types.Content(
        role="user",
        parts=[types.Part.from_text(text=user_message)],
    ))

    client = _get_client()

    buffer = ""
    for chunk in client.models.generate_content_stream(
        model=GEMINI_MODEL,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            max_output_tokens=MAX_TOKENS,
            temperature=0.7,
        ),
    ):
        if chunk.text:
            buffer += chunk.text
            # Yield complete sentences for TTS
            while True:
                for i, ch in enumerate(buffer):
                    if ch in ".!?" and (i + 1 == len(buffer) or buffer[i + 1] in " \n"):
                        sentence = buffer[: i + 1].strip()
                        buffer = buffer[i + 1 :].lstrip()
                        if sentence:
                            yield audit_response(sentence)
                        break
                else:
                    break

    # Yield any remaining text
    if buffer.strip():
        yield audit_response(buffer.strip())
