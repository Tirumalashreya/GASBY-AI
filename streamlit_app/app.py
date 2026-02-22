# GASBY-Streamlit/app.py

import streamlit as st
import boto3
import time
import uuid
import subprocess
import json
import tempfile
import cv2

# --------------------------------------------------
# AWS S3 CLIENT
# --------------------------------------------------
s3_client = boto3.client("s3", region_name="us-east-1")

SOURCE_BUCKET = "gasby-reqs"
TARGET_BUCKET = "gasby-action-result"

# --------------------------------------------------
# UTILITIES
# --------------------------------------------------

def get_video_duration(file):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_file:
        tmp_file.write(file.read())
        tmp_file.flush()
        tmp_file_path = tmp_file.name

    cap = cv2.VideoCapture(tmp_file_path)
    if not cap.isOpened():
        st.error("Video capture error")
        return None, None

    fps = cap.get(cv2.CAP_PROP_FPS)

    result = subprocess.run(
        [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            tmp_file_path
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    duration = float(result.stdout.decode().strip())
    return duration, float(fps)


def upload_video_to_s3(file, folder_name):
    key = f"{folder_name}/{folder_name}.mp4"
    file.seek(0)

    st.write("📤 Uploading VIDEO to:")
    st.write("Bucket:", SOURCE_BUCKET)
    st.write("Key:", key)

    s3_client.upload_fileobj(file, SOURCE_BUCKET, key)

    st.success("✅ Video uploaded successfully")


def upload_json_to_s3(json_data, folder_name):
    key = f"{folder_name}/{folder_name}.json"

    st.write("📤 Uploading METADATA to:")
    st.write("Bucket:", SOURCE_BUCKET)
    st.write("Key:", key)

    s3_client.put_object(
        Bucket=SOURCE_BUCKET,
        Key=key,
        Body=json.dumps(json_data)
    )

    st.success("✅ Metadata uploaded successfully")


def commentary_exists(folder_name):
    try:
        key = f"{folder_name}/{folder_name}_commentary.json"
        s3_client.head_object(Bucket=TARGET_BUCKET, Key=key)
        return True
    except:
        return False


def get_video_url(folder_name):
    return f"https://{TARGET_BUCKET}.s3.amazonaws.com/{folder_name}/{folder_name}_broadcast.mp4"


# --------------------------------------------------
# UI
# --------------------------------------------------

st.title("🏀 AI Basketball Commentator")

team_a_color = st.selectbox("Team A Color",
                            ["Black", "Blue", "Green", "Purple",
                             "Red", "White", "Yellow", "Orange", "Unlabeled"])

team_b_color = st.selectbox("Team B Color",
                            ["Black", "Blue", "Green", "Purple",
                             "Red", "White", "Yellow", "Orange", "Unlabeled"])

language = st.selectbox("Language",
                        ["English", "Korean", "Spanish",
                         "French", "German", "Chinese", "Japanese"])

uploaded_file = st.file_uploader("Upload a video", type=["mp4"])
start_button = st.button("Start Processing")

# --------------------------------------------------
# PROCESS
# --------------------------------------------------

if uploaded_file and start_button:

    folder_name = str(uuid.uuid4())

    duration, fps = get_video_duration(uploaded_file)

    metadata = {
        "language": language,
        "team_a_color": team_a_color,
        "team_b_color": team_b_color,
        "video_duration": duration,
        "fps": fps
    }

    st.write("📁 Folder UUID:", folder_name)

    upload_video_to_s3(uploaded_file, folder_name)
    upload_json_to_s3(metadata, folder_name)

    st.success("🚀 Upload complete. Waiting for processing...")

    timeout = 600
    start_time = time.time()

    while not commentary_exists(folder_name):
        if time.time() - start_time > timeout:
            st.error("❌ Processing timeout.")
            st.stop()
        time.sleep(5)

    st.success("🎉 Processing complete!")

    video_url = get_video_url(folder_name)
    st.video(video_url)