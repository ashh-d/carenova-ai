// Vercel Serverless Function for CareNova AI (Node.js runtime)
// Zero external dependencies - uses native fetch, regex, and json

const CANDIDATE_MODELS = [
  "gemini-3.5-flash-lite",
  "gemini-3.1-flash-lite",
  "gemini-3.8-flash"
];

const SYSTEM_PROMPT = `You are **CareNova AI**, an intelligent, empathetic health information assistant designed to help users understand general health topics and symptoms safely. You speak in clear, simple, reassuring language. You support English, Hindi, and Marathi — reply in whichever language the user is using.

Rules you MUST follow at all times:
1. Never diagnose. You may describe what symptoms could relate to in general terms, but NEVER say "you have X" or "this is X."
2. Never prescribe medication or dosages. If asked about dosages, reply: "Dosages depend on age, weight, and medical history — please consult a doctor or pharmacist for the correct dose."
3. Never advise stopping or changing prescribed medication. Advise speaking with the prescribing doctor before making any changes.
4. Ask clarifying questions before giving information: duration, severity (1-10), other symptoms, age group, any known conditions.
5. Recommend a doctor whenever symptoms are: severe, persistent (>3 days), worsening, in an infant, or causing significant distress.
6. Keep answers SHORT — ideally 2-4 sentences.
7. Always end with a gentle nudge toward professional care when appropriate: "If this continues, please see a doctor."`;

const EMERGENCY_PATTERNS = [
  { regex: /\b(chest\s*pain|heart\s*attack|chest\s*tight(ness)?)\b/i, label: "chest pain" },
  { regex: /(सीने\s*में\s*दर्द|छाती\s*में\s*दर्द|हार्ट\s*अटैक)/i, label: "chest pain (Hindi)" },
  { regex: /\b(can'?t\s*breathe|difficulty\s*breathing|choking|suffocating)\b/i, label: "breathing difficulty" },
  { regex: /(सांस\s*(नहीं\s*आ|लेने\s*में\s*तकलीफ|फूलना))/i, label: "breathing difficulty (Hindi)" },
  { regex: /\b(stroke|sudden(ly)?\s*(numb(ness)?|confusion|can'?t\s*speak|vision\s*loss))\b/i, label: "possible stroke" },
  { regex: /\b(heavy\s*bleed(ing)?|uncontrolled\s*bleed(ing)?|won'?t\s*stop\s*bleed(ing)?)\b/i, label: "severe bleeding" },
  { regex: /(खून\s*बंद\s*नहीं)/i, label: "severe bleeding (Hindi)" },
  { regex: /\b(unconscious|passed\s*out|faint(ed|ing)?|not\s*responding)\b/i, label: "unconsciousness" },
  { regex: /(बेहोश)/i, label: "unconsciousness (Hindi)" },
  { regex: /\b(suicid(e|al)|kill\s*my\s*self|end\s*(my|it\s*all)|want\s*to\s*die|self[\s-]*harm)\b/i, label: "mental health crisis" },
  { regex: /(आत्महत्या|खुदकुशी|मरना\s*चाहत)/i, label: "mental health crisis (Hindi)" },
  { regex: /\b(anaphyla(xis|ctic)|throat\s*(is\s*)?swell(ing|s)?|face\s*(is\s*)?swell(ing|s)?)\b/i, label: "severe allergic reaction" },
  { regex: /\b(seizure|convuls(ion|ing)|fitting)\b/i, label: "seizure" },
  { regex: /(दौरा\s*(पड़|आ))/i, label: "seizure (Hindi)" },
  { regex: /\b(poison(ed|ing)?|overdos(e|ed|ing))\b/i, label: "poisoning / overdose" },
  { regex: /(ज़हर|विष|ओवरडोज़)/i, label: "poisoning / overdose (Hindi)" }
];

const EMERGENCY_EN = `🚨 **This sounds like it could be a medical emergency.**\n\nPlease take these steps **immediately**:\n\n1. **Call 112** (India emergency number) or go to the nearest emergency room.\n2. If you are experiencing a mental health crisis, please call:\n   - **iCall:** 9152987821\n   - **Vandrevala Foundation:** 1860-2662-345\n3. Stay with someone and do not delay seeking professional emergency care. 🙏`;

const EMERGENCY_HI = `🚨 **यह एक मेडिकल इमरजेंसी हो सकती है।**\n\nकृपया **तुरंत** ये कदम उठाएं:\n\n1. **112 पर तुरंत कॉल करें** या नज़दीकी आपातकालीन अस्पताल जाएं।\n2. यदि आप मानसिक संकट या तनाव में हैं, तो कॉल करें:\n   - **iCall:** 9152987821\n   - **वंद्रेवाला फाउंडेशन:** 1860-2662-345\n3. किसी परिजन के साथ रहें और तुरंत मदद लें। 🙏`;

function detectEmergency(text) {
  for (const item of EMERGENCY_PATTERNS) {
    if (item.regex.test(text)) {
      return {
        isEmergency: true,
        label: item.label,
        response: item.label.includes("Hindi") ? EMERGENCY_HI : EMERGENCY_EN
      };
    }
  }
  return { isEmergency: false, label: null, response: "" };
}

function auditResponse(text) {
  let notes = "";
  if (/\b\d+\s*(mg|ml|tablet|capsule|drop|dose)\b/i.test(text)) {
    notes += "\n\n⚠️ *Note: Specific dosages depend on individual medical factors. Please consult a doctor or pharmacist.*";
  }
  if (/\byou\s+(have|are\s+suffering\s+from|are\s+diagnosed)\b/i.test(text)) {
    notes += "\n\n⚠️ *Note: Only a qualified physician can provide an official medical diagnosis.*";
  }
  return text + notes;
}

export default async function handler(req, res) {
  // Set CORS headers
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "POST, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");

  if (req.method === "OPTIONS") {
    return res.status(200).end();
  }

  if (req.method !== "POST") {
    return res.status(405).json({ error: "Method not allowed" });
  }

  try {
    const { message, history = [] } = req.body || {};
    if (!message || !message.trim()) {
      return res.status(400).json({ error: "Empty message" });
    }

    const trimmedMsg = message.trim();

    // 1. Pre-LLM Emergency check
    const emergency = detectEmergency(trimmedMsg);
    if (emergency.isEmergency) {
      return res.status(200).json({
        response: emergency.response,
        is_emergency: true,
        emergency_label: emergency.label
      });
    }

    // 2. Prepare Gemini payload
    const apiKey = process.env.GEMINI_API_KEY;
    if (!apiKey) {
      return res.status(500).json({ error: "GEMINI_API_KEY environment variable is not configured on Vercel." });
    }

    const contents = [];
    for (const msg of history) {
      contents.push({
        role: msg.role === "assistant" ? "model" : "user",
        parts: [{ text: msg.content || "" }]
      });
    }
    contents.push({
      role: "user",
      parts: [{ text: trimmedMsg }]
    });

    const payload = {
      system_instruction: { parts: [{ text: SYSTEM_PROMPT }] },
      contents,
      generationConfig: {
        temperature: 0.7,
        maxOutputTokens: 512
      }
    };

    let reply = null;
    let lastError = null;

    for (const model of CANDIDATE_MODELS) {
      const url = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${apiKey}`;
      try {
        const geminiRes = await fetch(url, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });

        if (geminiRes.ok) {
          const data = await geminiRes.json();
          const text = data?.candidates?.[0]?.content?.parts?.[0]?.text;
          if (text) {
            reply = auditResponse(text);
            break;
          }
        } else {
          const errData = await geminiRes.text();
          lastError = `Model ${model} returned ${geminiRes.status}: ${errData}`;
        }
      } catch (err) {
        lastError = err.message;
      }
    }

    if (!reply) {
      return res.status(200).json({
        response: "I apologize, I am temporarily experiencing connection delays. Please consult a healthcare professional.",
        is_emergency: false,
        emergency_label: null
      });
    }

    return res.status(200).json({
      response: reply,
      is_emergency: false,
      emergency_label: null
    });

  } catch (err) {
    return res.status(500).json({ error: err.message || "Internal server error" });
  }
}
