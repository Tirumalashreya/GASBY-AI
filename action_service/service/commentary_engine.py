# Gasby_Ai/action_service/service/commentary_engine.py

import requests
import json
import re
from dotenv import dotenv_values

env = dotenv_values(".env")
GEMINI_API_KEY = env.get("GEMINI_API_KEY")

GEMINI_MODEL = "models/gemini-2.5-flash"

GEMINI_URL = (
    f"https://generativelanguage.googleapis.com/v1/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
)


def clean_response(text):
    if not text:
        return None

    text = text.strip()
    text = re.sub(r"```json", "", text)
    text = re.sub(r"```", "", text)

    match = re.search(r"\[.*\]", text, re.DOTALL)
    return match.group(0) if match else None


def generate_gemini_commentary(timeline):

    if not timeline:
        print("⚠ No timeline for commentary.")
        return []

    system_prompt = """
You are a professional basketball broadcast team.

There are TWO commentators:
1. Mike – High energy play-by-play
2. Sarah – Tactical analyst

Rules:
- Alternate speakers
- Mention timestamps in seconds (numeric)
- Return ONLY valid JSON array
- No markdown
"""

    user_prompt = f"Game timeline:\n{json.dumps(timeline, indent=2)}"

    payload = {
        "contents": [{
            "parts": [{"text": system_prompt + "\n\n" + user_prompt}]
        }]
    }

    try:
        response = requests.post(
            GEMINI_URL,
            json=payload,
            headers={"Content-Type": "application/json"}
        )

        response_json = response.json()

        print("\n🔎 FULL GEMINI RAW RESPONSE:\n")
        print(json.dumps(response_json, indent=2))
        print("========================================================\n")

        if "error" in response_json:
            print("❌ Gemini API Error:", response_json["error"])
            return []

        candidates = response_json.get("candidates", [])
        if not candidates:
            return []

        raw_text = candidates[0]["content"]["parts"][0]["text"]

        cleaned = clean_response(raw_text)
        if not cleaned:
            return []

        return json.loads(cleaned)

    except Exception as e:
        print("❌ Gemini request failed:", e)
        return []