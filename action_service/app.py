# GASBY-Action-Recog/app.py

import cv2
import json
import os
import shutil
import time
import boto3
import subprocess

from flask import Flask, request, jsonify
from flask_cors import CORS

from service.action_recognition import ActioRecognition, create_json
from service.commentary_engine import group_events
from service.hybrid_commentary import generate_hybrid_commentary
from service.tts_engine import generate_tts_audio_from_events

from utils.s3utils import download_file, upload_file
from entity.player import Player
from dotenv import dotenv_values


# ===============================
# LOAD ENV
# ===============================

env = dotenv_values(".env")

required_keys = [
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_DEFAULT_REGION"
]

for key in required_keys:
    if key not in env or not env[key]:
        raise Exception(f"❌ Missing {key} in .env")


# ===============================
# SAFE S3 INIT
# ===============================

s3 = boto3.client(
    "s3",
    aws_access_key_id=env["AWS_ACCESS_KEY_ID"].strip(),
    aws_secret_access_key=env["AWS_SECRET_ACCESS_KEY"].strip(),
    region_name=env["AWS_DEFAULT_REGION"].strip()
)

INPUT_BUCKET = "gasby-reqs"
MOT_BUCKET = "gasby-mot-resultss"
ACTION_BUCKET = "gasby-action-result"

app = Flask(__name__)
CORS(app)


@app.route("/action-predict")
def health():
    return "ok"


@app.route("/action-predict/predict", methods=["POST"])
def predict():

    start_time = time.time()
    data = request.get_json()

    if not data or "uuid" not in data:
        return jsonify({"error": "uuid missing"}), 400

    uuid = data["uuid"]

    try:
        # ===============================
        # 1️⃣ FIND VIDEO
        # ===============================
        response = s3.list_objects_v2(
            Bucket=INPUT_BUCKET,
            Prefix=f"{uuid}/"
        )

        objects = response.get("Contents", [])
        mp4_key = next(
            (obj["Key"] for obj in objects if obj["Key"].endswith(".mp4")),
            None
        )

        if not mp4_key:
            return jsonify({"error": "No mp4 found"}), 400

        mp4_file = os.path.basename(mp4_key)
        print("📥 Found video:", mp4_file)

        # ===============================
        # 2️⃣ DOWNLOAD FILES
        # ===============================
        download_file(INPUT_BUCKET, uuid, f"resources/{uuid}", mp4_file)
        download_file(MOT_BUCKET, uuid, f"resources/{uuid}", f"{uuid}.json")

        # ===============================
        # 3️⃣ LOAD VIDEO (FAST MODE 🚀)
        # ===============================
        video_path = f"resources/{uuid}/{mp4_file}"
        cap = cv2.VideoCapture(video_path)

        fps = cap.get(cv2.CAP_PROP_FPS)
        if not fps or fps <= 0:
            fps = 30

        frames = []
        frame_count = 0

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            # 🚀 SPEED BOOST: process every 3rd frame
            if frame_count % 3 == 0:
                frame = cv2.resize(frame, (640, 640))
                frames.append(frame)

            frame_count += 1

        cap.release()

        if not frames:
            return jsonify({"error": "No frames extracted"}), 400

        print("🎬 Frames loaded:", len(frames))
        print("🎬 FPS:", fps)

        # ===============================
        # 4️⃣ LOAD MOT JSON
        # ===============================
        with open(f"resources/{uuid}/{uuid}.json", "r") as f:
            mot_results = json.load(f)

        players = []

        for r in mot_results:
            player = Player(r["player_id"], r.get("team", "unknown"))
            player.bboxs = {
                p["frame"]: p["box"]
                for p in r.get("positions", [])
            }
            player.positions = {
                p["frame"]: p.get("position_name", "")
                for p in r.get("positions", [])
            }
            player.actions = {}
            players.append(player)

        # ===============================
        # 5️⃣ ACTION RECOGNITION
        # ===============================
        players, actions = ActioRecognition(frames, players)
        result_json = create_json(players, actions, frame_len=len(frames))

        os.makedirs(f"outputs/{uuid}", exist_ok=True)

        with open(f"outputs/{uuid}/{uuid}.json", "w") as f:
            json.dump(result_json, f, indent=4)

        # ===============================
        # 6️⃣ GROUP EVENTS
        # ===============================
        grouped_events = group_events(result_json)
        print("🧠 Grouped events:", len(grouped_events))

        if not grouped_events:
            grouped_events = [{
                "start_frame": 0,
                "end_frame": 10,
                "action": "no_action",
                "intensity": "low"
            }]

        # ===============================
        # 7️⃣ GENERATE COMMENTARY
        # ===============================
        commentary_output = []

        for event in grouped_events:
            commentary = generate_hybrid_commentary(event)
            commentary_output.append(commentary)

        commentary_json_path = f"outputs/{uuid}/{uuid}_commentary.json"

        with open(commentary_json_path, "w") as f:
            json.dump(commentary_output, f, indent=4)

        # ===============================
        # 8️⃣ TTS
        # ===============================
        audio_path = f"outputs/{uuid}/{uuid}_commentary.mp3"

        print("🎙 Generating TTS Audio...")
        duration = generate_tts_audio_from_events(
            commentary_output,
            audio_path,
            fps=fps
        )

        print("⏱ Audio Duration:", duration)

        if duration <= 0:
            raise Exception("Audio duration is zero.")

        # ===============================
        # 9️⃣ MERGE VIDEO + AUDIO
        # ===============================
        final_video_path = f"outputs/{uuid}/{uuid}_broadcast.mp4"

        ffmpeg_command = [
            "ffmpeg",
            "-y",
            "-i", video_path,
            "-i", audio_path,
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-c:v", "copy",
            "-shortest",
            final_video_path
        ]

        subprocess.run(ffmpeg_command, check=True)

        # ===============================
        # 🔟 UPLOAD TO S3
        # ===============================
        upload_file(ACTION_BUCKET, uuid, f"{uuid}.json", uuid)
        upload_file(ACTION_BUCKET, uuid, f"{uuid}_commentary.json", uuid)
        upload_file(ACTION_BUCKET, uuid, f"{uuid}_commentary.mp3", uuid)
        upload_file(ACTION_BUCKET, uuid, f"{uuid}_broadcast.mp4", uuid)

        shutil.rmtree(f"resources/{uuid}", ignore_errors=True)

        total_time = time.time() - start_time
        print("✅ Total Processing Time:", total_time)

        return jsonify({
            "status": "success",
            "uuid": uuid,
            "processing_time": total_time
        }), 200

    except Exception as e:
        print("❌ ERROR:", str(e))
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)