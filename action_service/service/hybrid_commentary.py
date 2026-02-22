#service/hybrid_commentary.py
from dotenv import dotenv_values

try:
    from google import genai
except ImportError:
    genai = None

env = dotenv_values(".env")
GEMINI_KEY = env.get("GEMINI_API_KEY")

if GEMINI_KEY and genai:
    try:
        client = genai.Client(api_key=GEMINI_KEY)
        GEMINI_AVAILABLE = True
        print("✅ Gemini Initialized Successfully")
    except:
        client = None
        GEMINI_AVAILABLE = False
else:
    client = None
    GEMINI_AVAILABLE = False


def build_prompt(event):

    action = event.get("action")
    intensity = event.get("intensity")

    return f"""
You are generating LIVE professional ESPN basketball commentary.

Two commentators:
1) PlayByPlay → energetic, reacts to moment
2) Analyst → calm, tactical explanation

Action: {action}
Intensity: {intensity}

Rules:
- 4 alternating lines
- PlayByPlay starts
- Analyst explains the play
- If intensity HIGH → more excitement
- If LOW → controlled tone

Return strictly:

PlayByPlay: ...
Analyst: ...
PlayByPlay: ...
Analyst: ...
"""


def gemini_commentary(event):

    if not GEMINI_AVAILABLE:
        raise Exception("Gemini unavailable")

    prompt = build_prompt(event)

    response = client.models.generate_content(
        model="models/gemini-2.5-flash",
        contents=prompt
    )

    text = response.text.strip()

    lines = []

    for line in text.split("\n"):
        if ":" in line:
            role, content = line.split(":", 1)
            lines.append({
                "commentator": role.strip(),
                "text": content.strip()
            })

    if len(lines) < 4:
        raise Exception("Gemini parsing failed")

    return {
        "start_frame": event["start_frame"],
        "end_frame": event["end_frame"],
        "action": event["action"],
        "intensity": event["intensity"],
        "commentary": lines[:4]
    }


def generate_hybrid_commentary(event):
    try:
        return gemini_commentary(event)
    except:
        return {
            "start_frame": event["start_frame"],
            "end_frame": event["end_frame"],
            "action": event["action"],
            "intensity": event["intensity"],
            "commentary": [
                {"commentator": "PlayByPlay", "text": "The play is developing quickly here!"},
                {"commentator": "Analyst", "text": "Strong spacing and smart positioning on that sequence."},
                {"commentator": "PlayByPlay", "text": "Momentum starting to build!"},
                {"commentator": "Analyst", "text": "That’s a well-structured offensive setup."}
            ]
        }
