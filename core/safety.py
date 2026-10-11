"""
Safety layer — pre-LLM emergency detection.

Runs *before* the message reaches the LLM so that emergency responses are
instant and deterministic (no risk of the model hallucinating around them).
"""

from __future__ import annotations

import re

# ── Emergency keyword patterns ──────────────────────────────────────────
# Each tuple: (compiled regex, human-readable label)
_EMERGENCY_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # Cardiac
    (re.compile(r"\b(chest\s*pain|heart\s*attack|chest\s*tight(ness)?)\b", re.I), "chest pain"),
    (re.compile(r"\b(सीने\s*में\s*दर्द|छाती\s*में\s*दर्द|हार्ट\s*अटैक)\b", re.I), "chest pain (Hindi)"),

    # Breathing
    (re.compile(r"\b(can'?t\s*breathe|difficulty\s*breathing|choking|suffocating)\b", re.I), "breathing difficulty"),
    (re.compile(r"\b(सांस\s*(नहीं\s*आ|लेने\s*में\s*तकलीफ|फूलना))\b", re.I), "breathing difficulty (Hindi)"),

    # Stroke
    (re.compile(
        r"\b(stroke|sudden(ly)?\s*(numb(ness)?|confusion|can'?t\s*speak|vision\s*loss))\b", re.I
    ), "possible stroke"),

    # Bleeding
    (re.compile(r"\b(heavy\s*bleed(ing)?|uncontrolled\s*bleed(ing)?|won'?t\s*stop\s*bleed(ing)?)\b", re.I), "severe bleeding"),
    (re.compile(r"\b(खून\s*बंद\s*नहीं)\b", re.I), "severe bleeding (Hindi)"),

    # Unconsciousness
    (re.compile(r"\b(unconscious|passed\s*out|faint(ed|ing)?|not\s*responding)\b", re.I), "unconsciousness"),
    (re.compile(r"\b(बेहोश)\b", re.I), "unconsciousness (Hindi)"),

    # Self-harm / Suicide
    (re.compile(
        r"\b(suicid(e|al)|kill\s*my\s*self|end\s*(my|it\s*all)|want\s*to\s*die|self[\s-]*harm)\b", re.I
    ), "mental health crisis"),
    (re.compile(r"(आत्महत्या|खुदकुशी|मरना\s*चाहत)", re.I), "mental health crisis (Hindi)"),

    # Allergic reaction
    (re.compile(r"\b(anaphyla(xis|ctic)|throat\s*(is\s*)?swell(ing|s)?|face\s*(is\s*)?swell(ing|s)?)\b", re.I), "severe allergic reaction"),

    # Seizure
    (re.compile(r"\b(seizure|convuls(ion|ing)|fitting)\b", re.I), "seizure"),
    (re.compile(r"\b(दौरा\s*(पड़|आ))\b", re.I), "seizure (Hindi)"),

    # Poisoning
    (re.compile(r"\b(poison(ed|ing)?|overdos(e|ed|ing))\b", re.I), "poisoning / overdose"),
    (re.compile(r"\b(ज़हर|विष|ओवरडोज़)\b", re.I), "poisoning / overdose (Hindi)"),
]

# ── Deterministic emergency response ────────────────────────────────────
_EMERGENCY_RESPONSE_EN = (
    "🚨 **This sounds like it could be a medical emergency.**\n\n"
    "Please take these steps **immediately**:\n\n"
    "1. **Call 112** (India emergency number) or go to the nearest hospital.\n"
    "2. If you're having thoughts of self-harm, please call:\n"
    "   - **iCall:** 9152987821\n"
    "   - **Vandrevala Foundation:** 1860-2662-345\n"
    "3. Stay with someone if possible and **do not delay** seeking help.\n\n"
    "I'm here to talk, but right now getting professional help is the most "
    "important thing. 🙏"
)

_EMERGENCY_RESPONSE_HI = (
    "🚨 **यह एक मेडिकल इमरजेंसी हो सकती है।**\n\n"
    "कृपया **तुरंत** ये कदम उठाएं:\n\n"
    "1. **112 पर कॉल करें** या नज़दीकी अस्पताल जाएं।\n"
    "2. अगर आप आत्महत्या के विचार कर रहे हैं, तो कॉल करें:\n"
    "   - **iCall:** 9152987821\n"
    "   - **वंद्रेवाला फाउंडेशन:** 1860-2662-345\n"
    "3. किसी के साथ रहें और मदद लेने में **देरी न करें**।\n\n"
    "मैं बात करने के लिए यहाँ हूँ, लेकिन अभी प्रोफेशनल मदद लेना सबसे ज़रूरी है। 🙏"
)


def detect_emergency(text: str) -> tuple[bool, str | None, str]:
    """Check user text for emergency signals.

    Returns:
        (is_emergency, matched_label, emergency_response)
    """
    for pattern, label in _EMERGENCY_PATTERNS:
        if pattern.search(text):
            # Pick Hindi response if Hindi patterns matched
            if "(Hindi)" in label:
                return True, label, _EMERGENCY_RESPONSE_HI
            return True, label, _EMERGENCY_RESPONSE_EN
    return False, None, ""


# ── Post-LLM guardrail check ────────────────────────────────────────────
_DOSAGE_LEAK = re.compile(
    r"\b\d+\s*(mg|ml|tablet|capsule|drop|dose)\b", re.I
)

_DIAGNOSIS_LEAK = re.compile(
    r"\byou\s+(have|are\s+suffering\s+from|are\s+diagnosed)\b", re.I
)


def audit_response(response: str) -> str:
    """Post-process LLM output to catch guardrail leaks.

    If the model accidentally includes a dosage number or a direct diagnosis,
    append a corrective note.
    """
    notes: list[str] = []
    if _DOSAGE_LEAK.search(response):
        notes.append(
            "\n\n⚠️ *Note: Specific dosages depend on individual factors. "
            "Please consult a doctor or pharmacist for the correct dose.*"
        )
    if _DIAGNOSIS_LEAK.search(response):
        notes.append(
            "\n\n⚠️ *Note: Only a qualified healthcare professional can "
            "provide a diagnosis. The above is general information only.*"
        )
    return response + "".join(notes)
