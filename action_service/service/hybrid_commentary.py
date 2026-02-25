# Gasby-Ai/action_service/service/hybrid_commentary.py

# Gasby-Ai/action_service/service/hybrid_commentary.py

import requests
import json
import re
from dotenv import dotenv_values

env = dotenv_values(".env")

GEMINI_API_KEY = env.get("GEMINI_API_KEY")

GEMINI_URL = (
    f"https://generativelanguage.googleapis.com/v1/models/"
    f"gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
)


# ---------------------------------------------------------
# 🔥 Helper: Clean Gemini Response Safely
# ---------------------------------------------------------

def clean_gemini_response(raw_text):
    if not raw_text:
        return None

    text = raw_text.strip()

    # Remove markdown code blocks
    text = re.sub(r"```json", "", text)
    text = re.sub(r"```", "", text)

    # Extract JSON array safely
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if match:
        return match.group(0)

    return text


# ---------------------------------------------------------
# 🎙 Hybrid Commentary Generator
# ---------------------------------------------------------

def generate_hybrid_commentary(events):

    if not events:
        print("⚠ No events for commentary.")
        return []

    system_prompt = """
You are a professional basketball broadcast team.

There are TWO commentators:

1. Mike – High energy, emotional, hype commentator
2. Sarah – Tactical analyst, calm and insightful

Strict Rules:
- Alternate speakers
- Mention timestamps in seconds (numeric, not string)
- Speak like live broadcast
- Keep commentary concise (2–4 lines per event)
- Do NOT use markdown
- Return ONLY valid JSON
- Do NOT wrap in backticks
- Do NOT add explanations

Required Format:

[
  {
    "timestamp": 12.5,
    "commentary": [
        {"speaker": "Mike", "text": "..."},
        {"speaker": "Sarah", "text": "..."}
    ]
  }
]
"""

    user_prompt = f"""
Game events:
{json.dumps(events, indent=2)}

Generate commentary aligned exactly to event frames converted to seconds.
"""

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": system_prompt + "\n" + user_prompt}
                ]
            }
        ]
    }

    try:
        response = requests.post(
            GEMINI_URL,
            json=payload,
            headers={"Content-Type": "application/json"}
        )

        if response.status_code != 200:
            print("❌ Gemini API error:", response.text)
            return []

        response_json = response.json()

        # Safety check
        if "candidates" not in response_json:
            print("❌ Gemini returned no candidates:", response_json)
            return []

        raw_text = response_json["candidates"][0]["content"]["parts"][0]["text"]

        cleaned_text = clean_gemini_response(raw_text)

        if not cleaned_text:
            print("❌ Empty Gemini response.")
            return []

        parsed_output = json.loads(cleaned_text)

        # Validate structure
        if not isinstance(parsed_output, list):
            print("❌ Invalid JSON structure.")
            return []

        print("\n🎙 Generated Commentary:\n")

        for event in parsed_output:
            print(f"⏱ Timestamp: {event['timestamp']} sec")
            for line in event["commentary"]:
                print(f"{line['speaker']}: {line['text']}")
            print("-" * 50)

        return parsed_output

    except json.JSONDecodeError as e:
        print("❌ JSON parsing error:", e)
        print("Raw Gemini output:", raw_text)
        return []

    except Exception as e:
        print("⚠ Gemini processing failed:", e)
        return []