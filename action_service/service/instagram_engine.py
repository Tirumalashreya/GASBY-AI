import requests
import time

GRAPH_BASE = "https://graph.facebook.com/v19.0"


def wait_until_ready(container_id, access_token):

    status_url = f"{GRAPH_BASE}/{container_id}"

    for _ in range(20):  # wait up to 100 seconds

        response = requests.get(
            status_url,
            params={
                "fields": "status_code",
                "access_token": access_token
            }
        )

        status = response.json().get("status_code")
        print("⏳ Processing Status:", status)

        if status == "FINISHED":
            return True

        if status == "ERROR":
            return False

        time.sleep(5)

    return False


def post_single_video(video_url, caption, access_token, ig_user_id):

    print(f"📲 Creating IG container for: {video_url}")

    container_url = f"{GRAPH_BASE}/{ig_user_id}/media"

    container_payload = {
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "access_token": access_token
    }

    container_response = requests.post(container_url, data=container_payload)
    container_json = container_response.json()

    print("📦 IG Container Response:", container_json)

    container_id = container_json.get("id")

    if not container_id:
        print("❌ Container creation failed")
        return container_json

    # Wait until Instagram finishes processing
    ready = wait_until_ready(container_id, access_token)

    if not ready:
        print("❌ Media processing failed")
        return {"error": "Media not ready"}

    publish_url = f"{GRAPH_BASE}/{ig_user_id}/media_publish"

    publish_payload = {
        "creation_id": container_id,
        "access_token": access_token
    }

    publish_response = requests.post(publish_url, data=publish_payload)
    publish_json = publish_response.json()

    print("🚀 IG Publish Response:", publish_json)

    return publish_json


def post_broadcast_and_highlights(
    broadcast_url,
    highlight_url,
    access_token,
    ig_user_id
):

    results = {}

    if broadcast_url:
        print("🎬 Posting Broadcast to Instagram...")
        results["broadcast"] = post_single_video(
            video_url=broadcast_url,
            caption="🏀 AI Generated Full Match Broadcast",
            access_token=access_token,
            ig_user_id=ig_user_id
        )

    if highlight_url:
        print("🔥 Posting Highlights to Instagram...")
        results["highlights"] = post_single_video(
            video_url=highlight_url,
            caption="🔥 AI Generated Match Highlights",
            access_token=access_token,
            ig_user_id=ig_user_id
        )

    return results