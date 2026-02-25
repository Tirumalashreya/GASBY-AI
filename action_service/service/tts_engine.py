# Gasby_Ai/action_service/service/tts_engine.py

import os
import requests
import base64
import subprocess
from dotenv import dotenv_values

env = dotenv_values(".env")

API_KEY = env.get("GOOGLE_TTS_API_KEY")
GOOGLE_TTS_URL = "https://texttospeech.googleapis.com/v1/text:synthesize"


# ---------------------------------------------------------
# GOOGLE TTS SYNTHESIZER
# ---------------------------------------------------------

def synthesize(text, voice_name, output_file):

    if not API_KEY:
        print("❌ GOOGLE_TTS_API_KEY missing in .env")
        return False

    print("\n🎤 Sending to Google TTS:")
    print("Text:", text[:80])
    print("Voice:", voice_name)

    payload = {
        "input": {"text": text},
        "voice": {
            "languageCode": "en-US",
            "name": voice_name
        },
        "audioConfig": {
            "audioEncoding": "MP3"
        }
    }

    response = requests.post(
        GOOGLE_TTS_URL,
        params={"key": API_KEY},
        json=payload
    )

    print("🔎 TTS Status Code:", response.status_code)

    if response.status_code != 200:
        print("❌ TTS Error Response:")
        print(response.text)
        return False

    data = response.json()

    if "audioContent" not in data:
        print("❌ No audioContent in TTS response")
        print(data)
        return False

    with open(output_file, "wb") as f:
        f.write(base64.b64decode(data["audioContent"]))

    print("✅ Audio clip generated:", output_file)

    return True


# ---------------------------------------------------------
# GENERATE FULL COMMENTARY AUDIO
# ---------------------------------------------------------

def generate_tts_audio_from_events(events, output_path):

    if not events:
        print("⚠ No commentary events. Skipping TTS.")
        return False

    if not isinstance(events, list):
        print("❌ Commentary format invalid. Expected list.")
        print("Type received:", type(events))
        return False

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    temp_files = []
    index = 0

    for event in events:

        # Skip invalid entries
        if not isinstance(event, dict):
            print("⚠ Skipping invalid event (not dict):", event)
            continue

        # -------------------------------------------------
        # CASE 1: NEW GEMINI FORMAT
        # { "speaker": "...", "timestamp": ..., "comment": "..." }
        # -------------------------------------------------
        if "comment" in event:

            speaker = event.get("speaker")
            text = event.get("comment")

            if not text:
                continue

            temp_file = f"temp_{index}.mp3"
            voice = "en-US-Neural2-D" if speaker == "Mike" else "en-US-Neural2-F"

            if synthesize(text, voice, temp_file):
                temp_files.append(temp_file)
                index += 1

        # -------------------------------------------------
        # CASE 2: OLD STRUCTURE
        # { "commentary": [ {speaker,text}, ... ] }
        # -------------------------------------------------
        elif "commentary" in event:

            commentary_list = event.get("commentary", [])

            if not isinstance(commentary_list, list):
                continue

            for line in commentary_list:

                if not isinstance(line, dict):
                    continue

                speaker = line.get("speaker")
                text = line.get("text")

                if not text:
                    continue

                temp_file = f"temp_{index}.mp3"
                voice = "en-US-Neural2-D" if speaker == "Mike" else "en-US-Neural2-F"

                if synthesize(text, voice, temp_file):
                    temp_files.append(temp_file)
                    index += 1

    # ---------------------------------------------------------
    # IF NO AUDIO CREATED
    # ---------------------------------------------------------
    if not temp_files:
        print("⚠ No audio clips generated.")
        return False

    print("\n🔊 Merging audio clips...")

    with open("file_list.txt", "w") as f:
        for file in temp_files:
            f.write(f"file '{file}'\n")

    merge_process = subprocess.run([
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", "file_list.txt",
        "-c", "copy",
        output_path
    ])

    if merge_process.returncode != 0:
        print("❌ FFmpeg merge failed.")
        return False

    # Cleanup
    for file in temp_files:
        if os.path.exists(file):
            os.remove(file)

    if os.path.exists("file_list.txt"):
        os.remove("file_list.txt")

    if not os.path.exists(output_path):
        print("❌ Final merged MP3 not created.")
        return False

    print("✅ Commentary audio created:", output_path)
    return True