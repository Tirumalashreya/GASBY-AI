# Gasby_Ai/action_service/app.py

import cv2
import json
import os
import boto3
import subprocess
import traceback

from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import dotenv_values

from service.tracking import build_tracks
from service.action_recognition import run_action_recognition
from service.game_intelligence import enrich_game_intelligence
from service.highlight_engine import generate_highlights
from service.tts_engine import generate_tts_audio_from_events
from service.commentary_engine import generate_gemini_commentary
from service.instagram_engine import post_broadcast_and_highlights


# ---------------------------------------------------------
# ENVIRONMENT
# ---------------------------------------------------------

env = dotenv_values(".env")

IG_ACCESS_TOKEN = env.get("IG_ACCESS_TOKEN")
IG_USER_ID = env.get("IG_USER_ID")

s3 = boto3.client(
    "s3",
    aws_access_key_id=env.get("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=env.get("AWS_SECRET_ACCESS_KEY"),
    region_name="us-east-1"
)

VIDEO_BUCKET = "gasby-reqs"
DETECTION_BUCKET = "gasby-mot-resultss"
OUTPUT_BUCKET = "gasby-action-result"

app = Flask(__name__)
CORS(app)


# ---------------------------------------------------------
# BUILD TIMELINE
# ---------------------------------------------------------

def build_timeline(events, fps):
    timeline = []
    for e in events:
        timeline.append({
            "timestamp": round(e["frame"] / fps, 2),
            "type": e.get("type"),
            "team": e.get("team"),
            "zone": e.get("zone"),
            "points": e.get("points"),
            "intensity": e.get("intensity")
        })
    return timeline


# ---------------------------------------------------------
# MAIN ROUTE
# ---------------------------------------------------------

@app.route("/action-predict/predict", methods=["POST"])
def predict():

    uuid = request.json.get("uuid")

    if not uuid:
        return jsonify({"status": "error", "message": "UUID missing"}), 400

    print("\n================ NEW REQUEST ================")
    print("UUID:", uuid)

    local_path = f"resources/{uuid}"
    output_path = f"outputs/{uuid}"

    os.makedirs(local_path, exist_ok=True)
    os.makedirs(output_path, exist_ok=True)

    try:

        # -------------------------------------------------
        # DOWNLOAD FROM S3
        # -------------------------------------------------

        print("⬇ Downloading video + detection JSON...")

        video_path = f"{local_path}/{uuid}.mp4"
        json_path = f"{local_path}/frame_level_detection.json"

        s3.download_file(VIDEO_BUCKET, f"{uuid}/{uuid}.mp4", video_path)
        s3.download_file(DETECTION_BUCKET, f"{uuid}/frame_level_detection.json", json_path)

        with open(json_path) as f:
            frame_data = json.load(f)

        # -------------------------------------------------
        # GET FPS
        # -------------------------------------------------

        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        cap.release()

        print("🎥 FPS:", fps)

        # -------------------------------------------------
        # TRACKING
        # -------------------------------------------------

        tracked_players = build_tracks(frame_data)

        # -------------------------------------------------
        # LOAD FRAMES
        # -------------------------------------------------

        cap = cv2.VideoCapture(video_path)
        video_frames = []

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            video_frames.append(frame)

        cap.release()

        # -------------------------------------------------
        # ACTION RECOGNITION
        # -------------------------------------------------

        cnn_events = run_action_recognition(video_frames, tracked_players)

        # -------------------------------------------------
        # GAME INTELLIGENCE
        # -------------------------------------------------

        enriched_events = enrich_game_intelligence(
            players=tracked_players,
            fps=fps,
            frame_detections=frame_data,
            cnn_events=cnn_events
        )

        # -------------------------------------------------
        # FILTER EVENTS
        # -------------------------------------------------

        filtered_events = []
        MIN_FRAME_GAP = int(fps * 5)
        last_frame = -9999

        for e in enriched_events:
            if e["frame"] - last_frame >= MIN_FRAME_GAP:
                filtered_events.append(e)
                last_frame = e["frame"]

        timeline = build_timeline(filtered_events, fps)

        # -------------------------------------------------
        # GEMINI COMMENTARY
        # -------------------------------------------------

        print("🎙 Generating commentary...")
        commentary = generate_gemini_commentary(timeline)

        if not commentary:
            print("⚠ Using fallback commentary.")
            commentary = [{
                "timestamp": 0.0,
                "commentary": [
                    {"speaker": "Mike", "text": "Welcome to tonight’s basketball action!"},
                    {"speaker": "Sarah", "text": "Both teams are ready to compete."}
                ]
            }]

        # -------------------------------------------------
        # TTS
        # -------------------------------------------------

        audio_path = f"{output_path}/{uuid}_commentary.mp3"

        tts_success = generate_tts_audio_from_events(commentary, audio_path)

        if not tts_success:
            print("❌ TTS failed.")
            return jsonify({"status": "error", "message": "TTS failed"}), 500

        # -------------------------------------------------
        # MERGE BROADCAST VIDEO
        # -------------------------------------------------

        final_video = f"{output_path}/{uuid}_broadcast.mp4"

        print("🎬 Merging broadcast video...")

        merge_process = subprocess.run([
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", audio_path,
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            "-c:a", "aac",
            final_video
        ])

        if merge_process.returncode != 0 or not os.path.exists(final_video):
            print("❌ Broadcast video creation failed.")
            return jsonify({"status": "error", "message": "Broadcast merge failed"}), 500

        # -------------------------------------------------
        # HIGHLIGHTS
        # -------------------------------------------------

        highlight_video_path = f"{output_path}/{uuid}_highlights.mp4"

        generate_highlights(
            video_path,
            filtered_events,
            fps,
            highlight_video_path
        )

        # -------------------------------------------------
        # UPLOAD TO S3
        # -------------------------------------------------

        print("☁ Uploading to S3...")

        broadcast_key = f"{uuid}/{uuid}_broadcast.mp4"
        highlight_key = f"{uuid}/{uuid}_highlights.mp4"

        if os.path.exists(final_video):
            s3.upload_file(final_video, OUTPUT_BUCKET, broadcast_key)
        else:
            return jsonify({"status": "error", "message": "Broadcast missing"}), 500

        if os.path.exists(highlight_video_path):
            s3.upload_file(highlight_video_path, OUTPUT_BUCKET, highlight_key)
        else:
            print("⚠ Highlight video not generated. Skipping upload.")

        broadcast_url = f"https://{OUTPUT_BUCKET}.s3.amazonaws.com/{broadcast_key}"
        highlight_url = f"https://{OUTPUT_BUCKET}.s3.amazonaws.com/{highlight_key}"

        # -------------------------------------------------
        # INSTAGRAM POST
        # -------------------------------------------------

        print("🚀 Posting to Instagram...")

        ig_results = post_broadcast_and_highlights(
            broadcast_url=broadcast_url,
            highlight_url=highlight_url,
            access_token=IG_ACCESS_TOKEN,
            ig_user_id=IG_USER_ID
        )

        print("📲 Instagram Results:", ig_results)

        print("✅ PROCESS COMPLETE")

        return jsonify({
            "status": "success",
            "instagram": ig_results
        })

    except Exception:
        print("🔥 ERROR OCCURRED")
        print(traceback.format_exc())
        return jsonify({"status": "error"}), 500


if __name__ == "__main__":
    app.run(port=5001, debug=False)