from TTS.api import TTS

# Load model (first time downloads ~1GB)
tts = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2")

text = "This is a test commentary voice."

tts.tts_to_file(
    text=text,
    file_path="test_voice.wav"
)

print("Voice generated successfully!")
