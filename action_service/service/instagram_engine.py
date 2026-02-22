#service/instagram_engine.py
import requests


def post_to_instagram(video_url, caption, access_token, ig_user_id):

    # Step 1: Create container
    container_url = f"https://graph.facebook.com/v19.0/{ig_user_id}/media"

    container_payload = {
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "access_token": access_token
    }

    container_response = requests.post(container_url, data=container_payload)
    container_id = container_response.json().get("id")

    if not container_id:
        return container_response.json()

    # Step 2: Publish
    publish_url = f"https://graph.facebook.com/v19.0/{ig_user_id}/media_publish"

    publish_payload = {
        "creation_id": container_id,
        "access_token": access_token
    }

    publish_response = requests.post(publish_url, data=publish_payload)

    return publish_response.json()
