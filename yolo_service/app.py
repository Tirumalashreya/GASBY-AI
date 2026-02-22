#GASBY-flask/app.py
from flask import Flask, jsonify, request   # ✅ ADD THIS
import cv2
import boto3
import shutil
import os
import json
import time
from flask_cors import CORS
from video_handler import VideoHandler
from dotenv import dotenv_values

# ==============================
# LOAD ENV
# ==============================

env = dotenv_values('.env')

print("🔐 Loading AWS credentials...")

s3 = boto3.client(
    's3',
    aws_access_key_id=env['AWS_ACCESS_KEY_ID'],
    aws_secret_access_key=env['AWS_SECRET_ACCESS_KEY'],
    region_name=env['AWS_REGION']
)

BUCKET_NAME = 'gasby-reqs'
RESULT_BUCKET = 'gasby-mot-resultss'

print("📦 Using INPUT bucket:", BUCKET_NAME)
print("📦 Using RESULT bucket:", RESULT_BUCKET)

# ==============================
# FLASK INIT
# ==============================

app = Flask(__name__)
CORS(app)


@app.route("/yolo-predict/upload", methods=["POST"])
def get_video():

    print("\n==============================")
    print("🚀 YOLO API CALLED")
    print("==============================")

    start_time = time.time()

    try:
        data = request.get_json()
        print("📩 Payload received:", data)

        if not data or "payload" not in data:
            print("❌ No payload received")
            return jsonify({"error": "Missing payload"}), 400

        payload = data.get('payload')
        print("📁 UUID:", payload)

        print("🔍 Listing S3 files...")
        response = s3.list_objects_v2(
            Bucket=BUCKET_NAME,
            Prefix=payload + "/"
        )

        files = [obj['Key'] for obj in response.get('Contents', [])]
        print("📄 Files found in S3:", files)

        video_file = next((f for f in files if f.endswith(".mp4")), None)
        json_file = next(
    (f for f in files if f.endswith(f"{payload}.json")),
    None
)

        if not video_file or not json_file:
            print("❌ Missing mp4/json in S3")
            return jsonify({"error": "Missing mp4/json"}), 400

        local_dir = f'./video/{payload}'
        os.makedirs(local_dir, exist_ok=True)

        local_video = f'{local_dir}/{os.path.basename(video_file)}'
        local_json = f'{local_dir}/{os.path.basename(json_file)}'

        print("⬇ Downloading video:", video_file)
        s3.download_file(BUCKET_NAME, video_file, local_video)

        print("⬇ Downloading metadata:", json_file)
        s3.download_file(BUCKET_NAME, json_file, local_json)

        print("✅ Download complete")

        with open(local_json) as f:
            meta = json.load(f)

        teamA = meta.get('team_a_color')
        teamB = meta.get('team_b_color')

        print("🎨 Team A:", teamA)
        print("🎨 Team B:", teamB)

        print("🎯 Running YOLO detectors...")

        video = cv2.VideoCapture(local_video)
        handler = VideoHandler(video)
        handler.run_detectors(local_dir, teamA, teamB)

        print("✅ YOLO detection finished")

        ball_path = f'{local_dir}/ball.json'
        player_path = f'{local_dir}/player_positions_filtered.json'

        if os.path.exists(ball_path):
            print("📤 Uploading ball.json")
            s3.upload_file(ball_path, RESULT_BUCKET, f'{payload}/{payload}_ball.json')

        if os.path.exists(player_path):
            print("📤 Uploading player_positions_filtered.json")
            s3.upload_file(player_path, RESULT_BUCKET, f'{payload}/{payload}.json')

        print("✅ Results uploaded to:", RESULT_BUCKET)

        shutil.rmtree(local_dir)
        print("🧹 Cleaned local directory")

        total_time = time.time() - start_time
        print("⏱ Processing time:", total_time)
        print("🎉 YOLO PROCESS COMPLETE\n")

        return jsonify({
            "message": "YOLO processing complete",
            "processing_time": total_time
        })

    except Exception as e:
        print("❌ ERROR IN YOLO SERVICE:", str(e))
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)