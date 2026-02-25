#Gasby-Ai/action_service/event_enricher.py
def enrich_events(events, fps):

    enriched = []

    for event in events:

        duration_frames = event["end_frame"] - event["start_frame"]
        duration_sec = duration_frames / fps

        enriched_event = event.copy()

        enriched_event["duration_sec"] = round(duration_sec, 2)

        # 🔥 Detect fast break
        if event["action"] == "run" and duration_sec < 2:
            enriched_event["play_type"] = "fast break"

        # 🔥 Detect long possession
        elif event["action"] == "ball in hand" and duration_sec > 3:
            enriched_event["play_type"] = "isolation play"

        # 🔥 Shot attempt
        elif event["action"] == "shoot":
            enriched_event["play_type"] = "shot attempt"

        # 🔥 Block event
        elif event["action"] == "block":
            enriched_event["play_type"] = "defensive block"

        else:
            enriched_event["play_type"] = event["action"]

        enriched.append(enriched_event)

    return enriched