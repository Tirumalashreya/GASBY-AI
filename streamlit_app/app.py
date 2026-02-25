#Gasby-Ai/streamlit_app/app.py
import streamlit as st
import boto3
import uuid
import json
import requests
import time

s3_client = boto3.client("s3", region_name="us-east-1")

SOURCE_BUCKET = "gasby-reqs"
TARGET_BUCKET = "gasby-action-result"

YOLO_URL = "http://localhost:5000/yolo-predict/upload"
ACTION_URL = "http://localhost:5001/action-predict/predict"


def upload_video_to_s3(file, folder_name):
    key = f"{folder_name}/{folder_name}.mp4"
    file.seek(0)
    s3_client.upload_fileobj(file, SOURCE_BUCKET, key)


def upload_json_to_s3(json_data, folder_name):
    key = f"{folder_name}/{folder_name}.json"
    s3_client.put_object(
        Bucket=SOURCE_BUCKET,
        Key=key,
        Body=json.dumps(json_data)
    )


def video_exists(folder_name):
    try:
        s3_client.head_object(
            Bucket=TARGET_BUCKET,
            Key=f"{folder_name}/{folder_name}_broadcast.mp4"
        )
        return True
    except:
        return False


def highlight_exists(folder_name):
    try:
        s3_client.head_object(
            Bucket=TARGET_BUCKET,
            Key=f"{folder_name}/{folder_name}_highlights.mp4"
        )
        return True
    except:
        return False


def fetch_video(folder_name, highlight=False):
    if highlight:
        key = f"{folder_name}/{folder_name}_highlights.mp4"
    else:
        key = f"{folder_name}/{folder_name}_broadcast.mp4"

    obj = s3_client.get_object(Bucket=TARGET_BUCKET, Key=key)
    return obj["Body"].read()


st.title("🏀 AI Basketball Commentator")

team_a_color = st.selectbox("Team A Color",
                            ["Black", "Blue", "Green", "Purple",
                             "Red", "White", "Yellow", "Orange"])

team_b_color = st.selectbox("Team B Color",
                            ["Black", "Blue", "Green", "Purple",
                             "Red", "White", "Yellow", "Orange"])

uploaded_file = st.file_uploader("Upload a video", type=["mp4"])
start_button = st.button("Start Processing")

if uploaded_file and start_button:

    folder_name = str(uuid.uuid4())

    metadata = {
        "team_a_color": team_a_color,
        "team_b_color": team_b_color
    }

    st.write("📤 Uploading...")
    upload_video_to_s3(uploaded_file, folder_name)
    upload_json_to_s3(metadata, folder_name)

    st.write("🚀 Running YOLO...")
    requests.post(YOLO_URL, json={"payload": folder_name})

    st.write("🚀 Running Action Recognition...")
    requests.post(ACTION_URL, json={"uuid": folder_name})

    st.write("⏳ Processing...")

    timeout = 600
    start_time = time.time()

    while not video_exists(folder_name):
        if time.time() - start_time > timeout:
            st.error("❌ Timeout")
            st.stop()
        time.sleep(5)

    st.success("✅ Broadcast Ready")
    st.video(fetch_video(folder_name))

    if highlight_exists(folder_name):
        st.subheader("🔥 Highlights")
        st.video(fetch_video(folder_name, highlight=True))