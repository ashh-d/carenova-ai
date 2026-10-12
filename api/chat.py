"""
Vercel Serverless Function for CareNova AI.
Zero external dependencies (uses standard library urllib, json, re, os).
Includes:
- Pre-LLM Emergency Detection (English & Hindi)
- System Prompt & Safety Guardrails
- Google Gemini 3.5 API with automatic fallback
- Post-LLM Guardrail Audit
"""

import os
import json
import re
import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler

# ── API Key Configuration ───────────────────────────────────────────────
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
CANDIDATE_MODELS = ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-3.8-flash"]

# ── System Prompt & Guardrails ──────────────────────────────────────────
SYSTEM_PROMPT = """\
You are **CareNova AI**, an intelligent, empathetic health information assistant \
designed to help users understand general health topics and symptoms safely. You speak in \
clear, simple, reassuring language. You support English, Hindi, and Marathi — reply in \
whichever language the user is using.

### Rules you MUST follow at all times:
1. **Never diagnose.** You may describe what symptoms *could* relate to in \
   general terms ("these symptoms are sometimes associated with..."), but you \
   must NEVER say "you have X" or "this is X."
2. **Never prescribe medication or dosages.** If asked about dosages (e.g., \
   "how much paracetamol for my baby"), reply: "Dosages depend on age, weight, \
   and medical history — please consult a doctor or pharmacist for the correct dose."
3. **Never advise stopping or changing prescribed medication.** Advise speaking with \
   the prescribing doctor before making any changes.
4. **Ask clarifying questions** before giving information: duration, severity \
   (1-10), other symptoms, age group, any known conditions.
5. **Recommend a doctor** whenever symptoms are: severe, persistent (>3 days), \
   worsening, in an infant, or causing significant distress.
6. **Keep answers SHORT** — ideally 2-4 sentences. Use bullet points only when listing next steps.
7. **Always end with a gentle nudge** toward professional care when appropriate: \
   "If this continues, please see a doctor."
"""

# ── Pre-LLM Emergency Detection ────────────────────────────────────────
EMERGENCY_PATTERNS = [
    (re.compile(r"\b(chest\s*pain|heart\s*attack|chest\s*tight(ness)?)\b", re.I), "chest pain"),
    (re.compile(r"\b(सीने\s*में\s*दर्द|छाती\s*में\s*दर्द|हार्ट\s*अटैक)\b", re.I), "chest pain (Hindi)"),
    (re.compile(r"\b(can'?t\s*breathe|difficulty\s*breathing|choking|suffocating)\b", re.I), "breathing difficulty"),
    (re.compile(r"\b(सांस\s*(नहीं\s*आ|लेने\s*में\s*तकलीफ|फूलना))\b", re.I), "breathing difficulty (Hindi)"),
    (re.compile(r"\b(stroke|sudden(ly)?\s*(numb(ness)?|confusion|can'?t\s*speak|vision\s*loss))\b", re.I), "possible stroke"),
    (re.compile(r"\b(heavy\s*bleed(ing)?|uncontrolled\s*bleed(ing)?|won'?t\s*stop\s*bleed(ing)?)\b", re.I), "severe bleeding"),
    (re.compile(r"\b(खून\s*बंद\s*नहीं)\b", re.I), "severe bleeding (Hindi)"),
    (re.compile(r"\b(unconscious|passed\s*out|faint(ed|ing)?|not\s*responding)\b", re.I), "unconsciousness"),
    (re.compile(r"\b(बेहोश)\b", re.I), "unconsciousness (Hindi)"),
    (re.compile(r"\b(suicid(e|al)|kill\s*my\s*self|end\s*(my|it\s*all)|want\s*to\s*die|self[\s-]*harm)\b", re.I), "mental health crisis"),
    (re.compile(r"(आत्महत्या|खुदकुशी|मरना\s*चाहत)", re.I), "mental health crisis (Hindi)"),
    (re.compile(r"\b(anaphyla(xis|ctic)|throat\s*(is\s*)?swell(ing|s)?|face\s*(is\s*)?swell(ing|s)?)\b", re.I), "severe allergic reaction"),
    (re.compile(r"\b(seizure|convuls(ion|ing)|fitting)\b", re.I), "seizure"),
    (re.compile(r"\b(दौरा\s*(पड़|आ))\b", re.I), "seizure (Hindi)"),
    (re.compile(r"\b(poison(ed|ing)?|overdos(e|ed|ing))\b", re.I), "poisoning / overdose"),
    (re.compile(r"\b(ज़हर|विष|ओवरडोज़)\b", re.I), "poisoning / overdose (Hindi)"),
]

EMERGENCY_EN = (
    "🚨 **This sounds like it could be a medical emergency.**\n\n"
    "Please take these steps **immediately**:\n\n"
    "1. **Call 112** (India emergency number) or go to the nearest emergency room.\n"
    "2. If you are experiencing a mental health crisis, please call:\n"
    "   - **iCall:** 9152987821\n"
    "   - **Vandrevala Foundation:** 1860-2662-345\n"
    "3. Stay with someone and do not delay seeking professional emergency care. 🙏"
)

EMERGENCY_HI = (
    "🚨 **यह एक मेडिकल इमरजेंसी हो सकती है।**\n\n"
    "कृपया **तुरंत** ये कदम उठाएं:\n\n"
    "1. **112 पर तुरंत कॉल करें** या नज़दीकी आपातकालीन अस्पताल जाएं।\n"
    "2. यदि आप मानसिक संकट या तनाव में हैं, तो कॉल करें:\n"
    "   - **iCall:** 9152987821\n"
    "   - **वंद्रेवाला फाउंडेशन:** 1860-2662-345\n"
    "3. किसी परिजन के साथ रहें और तुरंत मदद लें। 🙏"
)

def detect_emergency(text: str):
    for pattern, label in EMERGENCY_PATTERNS:
        if pattern.search(text):
            response = EMERGENCY_HI if "(Hindi)" in label else EMERGENCY_EN
            return True, label, response
    return False, None, ""

# ── Post-LLM Audit ───────────────────────────────────────────────────────
DOSAGE_REGEX = re.compile(r"\b\d+\s*(mg|ml|tablet|capsule|drop|dose)\b", re.I)
DIAGNOSIS_REGEX = re.compile(r"\byou\s+(have|are\s+suffering\s+from|are\s+diagnosed)\b", re.I)

def audit_response(text: str) -> str:
    notes = []
    if DOSAGE_REGEX.search(text):
        notes.append("\n\n⚠️ *Note: Specific dosages depend on individual medical factors. Please consult a doctor or pharmacist.*")
    if DIAGNOSIS_REGEX.search(text):
        notes.append("\n\n⚠️ *Note: Only a qualified physician can provide an official medical diagnosis.*")
    return text + "".join(notes)

# ── Gemini REST Caller with Multi-Model Fallback ─────────────────────────
def call_gemini(user_message: str, history: list) -> str:
    api_key = os.environ.get("GEMINI_API_KEY", "")
    
    # Format contents for Gemini
    contents = []
    for msg in history:
        role = "model" if msg.get("role") == "assistant" else "user"
        contents.append({"role": role, "parts": [{"text": msg.get("content", "")}]})
    contents.append({"role": "user", "parts": [{"text": user_message}]})

    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": contents,
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 512
        }
    }
    data_bytes = json.dumps(payload).encode("utf-8")

    last_error = None
    for model in CANDIDATE_MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        req = urllib.request.Request(
            url,
            data=data_bytes,
            headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=12) as response:
                result = json.loads(response.read().decode("utf-8"))
                candidates = result.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        text = parts[0].get("text", "")
                        return audit_response(text)
        except Exception as e:
            last_error = e
            continue

    return f"I apologize, I am temporarily experiencing connection delays. Please consult a healthcare professional. (Detail: {last_error})"

# ── Vercel HTTP Handler ──────────────────────────────────────────────────
class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            data = json.loads(body) if body else {}

            user_message = data.get("message", "").strip()
            history = data.get("history", [])

            if not user_message:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Empty message"}).encode("utf-8"))
                return

            # Check pre-LLM emergency
            is_emergency, emergency_label, emergency_reply = detect_emergency(user_message)
            if is_emergency:
                reply = emergency_reply
            else:
                reply = call_gemini(user_message, history)

            response_data = {
                "response": reply,
                "is_emergency": is_emergency,
                "emergency_label": emergency_label
            }

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(response_data).encode("utf-8"))

        except Exception as err:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(err)}).encode("utf-8"))
