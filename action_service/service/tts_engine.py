# service/tts_engine.py

import os
from google.cloud import texttospeech
from google.oauth2 import service_account
from pydub import AudioSegment

SERVICE_ACCOUNT_PATH = "/Users/vyju/GASBY-Action-Recognition/gasby-tts-86f12d85ba68.json"


def generate_tts_audio_from_events(events, output_path, fps=30):

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    print("🎙 Using Google Cloud Text-to-Speech")

    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_PATH
    )

    client = texttospeech.TextToSpeechClient(credentials=credentials)

    final_audio = AudioSegment.empty()
    generated_segments = 0

    # 🚨 If no events at all
    if not events:
        print("⚠ No commentary events found. Generating fallback audio.")
        events = [{
            "commentary": [{
                "commentator": "system",
                "text": "Game analysis complete."
            }]
        }]

    for event in events:

        commentary_lines = event.get("commentary", [])
        if not commentary_lines:
            continue

        for line in commentary_lines:

            text = line.get("text", "").strip()
            speaker = line.get("commentator", "system").strip().lower()

            if not text:
                continue

            synthesis_input = texttospeech.SynthesisInput(text=text)

            if speaker == "playbyplay":
                voice = texttospeech.VoiceSelectionParams(
                    language_code="en-US",
                    name="en-US-Neural2-D"
                )
            else:
                voice = texttospeech.VoiceSelectionParams(
                    language_code="en-US",
                    name="en-US-Neural2-F"
                )

            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3
            )

            response = client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )

            if not response.audio_content:
                print("⚠ Empty audio content from Google TTS, skipping.")
                continue

            temp_file = os.path.join(os.path.dirname(output_path), "temp.mp3")

            with open(temp_file, "wb") as out:
                out.write(response.audio_content)

            try:
                segment = AudioSegment.from_mp3(temp_file)
                final_audio += segment
                final_audio += AudioSegment.silent(duration=400)
                generated_segments += 1
            except Exception as e:
                print("⚠ Error reading generated mp3:", e)

            os.remove(temp_file)

    # 🚨 If still nothing generated
    if generated_segments == 0:
        print("⚠ No valid TTS segments created. Generating emergency fallback.")
        fallback = AudioSegment.silent(duration=1000)
        final_audio = fallback

    final_audio.export(output_path, format="mp3")

    duration_seconds = len(final_audio) / 1000.0

    print(f"🎧 Audio saved locally at: {output_path}")
    print(f"⏱ Audio Duration: {duration_seconds:.2f} seconds")

    return duration_seconds