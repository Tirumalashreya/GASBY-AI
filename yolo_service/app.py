# Gasby-Ai/Yolo_service/app.py


from flask import Flask, jsonify, request
import cv2
import boto3
import shutil
import os
import json
import time
import traceback
from flask_cors import CORS
from video_handler import VideoHandler
from dotenv import dotenv_values


# -------------------------------------------------
# ENV + S3
# -------------------------------------------------

env = dotenv_values('.env')

s3 = boto3.client(
    's3',
    aws_access_key_id=env['AWS_ACCESS_KEY_ID'],
    aws_secret_access_key=env['AWS_SECRET_ACCESS_KEY'],
    region_name="us-east-1"
)

SOURCE_BUCKET = 'gasby-reqs'
RESULT_BUCKET = 'gasby-mot-resultss'


# -------------------------------------------------
# COLOR MAP (For color names support)
# -------------------------------------------------

COLOR_MAP = {
    "green": [0, 255, 0],
    "white": [255, 255, 255],
    "red": [0, 0, 255],
    "blue": [255, 0, 0],
    "yellow": [0, 255, 255],
    "black": [0, 0, 0],
    "orange": [0, 165, 255],
    "purple": [128, 0, 128]
}


def normalize_team_colors(raw_colors):
    """
    Accepts:
    {
        "Green Team": "green"
        OR
        "Green Team": [0,255,0]
    }
    """

    if not raw_colors:
        return {}

    normalized = {}

    for team_name, value in raw_colors.items():

        # If already BGR list
        if isinstance(value, list) and len(value) == 3:
            normalized[team_name] = value

        # If color name
        elif isinstance(value, str):
            color_lower = value.lower()
            if color_lower in COLOR_MAP:
                normalized[team_name] = COLOR_MAP[color_lower]

    return normalized


# -------------------------------------------------
# APP
# -------------------------------------------------

app = Flask(__name__)
CORS(app)


@app.route("/yolo-predict/upload", methods=["POST"])
def get_video():

    start_time = time.time()

    try:
        print("🚀 YOLO REQUEST RECEIVED")

        data = request.get_json()

        if not data or "payload" not in data:
            return jsonify({"error": "Missing payload"}), 400

        payload = data["payload"]

        # ----------------------------
        # 🔥 NEW: TEAM COLORS SUPPORT
        # ----------------------------

        raw_team_colors = data.get("team_colors", {})
        team_colors = normalize_team_colors(raw_team_colors)

        print("📦 UUID:", payload)
        print("🎨 Team Colors:", team_colors)

        local_dir = f'./video/{payload}'
        os.makedirs(local_dir, exist_ok=True)

        video_key = f"{payload}/{payload}.mp4"
        json_key = f"{payload}/{payload}.json"

        local_video = f"{local_dir}/{payload}.mp4"
        local_json = f"{local_dir}/{payload}.json"

        print("⬇ Downloading video + meta from S3...")

        s3.download_file(SOURCE_BUCKET, video_key, local_video)
        s3.download_file(SOURCE_BUCKET, json_key, local_json)

        print("✅ Download complete")

        # ----------------------------
        # Validate video
        # ----------------------------

        video = cv2.VideoCapture(local_video)

        if not video.isOpened():
            raise Exception("❌ Failed to open video file")

        # ----------------------------
        # 🔥 FIXED: PASS team_colors
        # ----------------------------

        handler = VideoHandler(video, team_colors)

        print("🧠 Running YOLO detection...")
        frame_data = handler.run_detectors(local_dir)

        detection_file = f"{local_dir}/frame_level_detection.json"

        if not os.path.exists(detection_file):
            raise Exception("❌ frame_level_detection.json not created")

        print("⬆ Uploading detection result to S3...")

        s3.upload_file(
            detection_file,
            RESULT_BUCKET,
            f"{payload}/frame_level_detection.json"
        )

        print("✅ Upload complete")

        shutil.rmtree(local_dir)

        return jsonify({
            "message": "YOLO complete",
            "time": round(time.time() - start_time, 2)
        })

    except Exception as e:
        print("\n🔥 YOLO SERVICE ERROR:")
        traceback.print_exc()
        print("\n")

        return jsonify({"error": str(e)}), 500


# -------------------------------------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)