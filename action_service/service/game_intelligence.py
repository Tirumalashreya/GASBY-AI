# Gasby_Ai/action_service/service/game_intelligence.py
# Gasby_Ai/action_service/service/game_intelligence.py

import math
from shapely.geometry import Point, Polygon


def distance(p1, p2):
    if not p1 or not p2:
        return 9999
    return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)


def calculate_speed(prev_pos, curr_pos):
    if not prev_pos or not curr_pos:
        return 0
    return distance(prev_pos, curr_pos)


def find_closest_player(ball, players):
    if not ball or not players:
        return None

    min_dist = 9999
    closest = None

    for p in players:
        d = distance(ball, p["center"])
        if d < min_dist:
            min_dist = d
            closest = p

    return closest


def enrich_game_intelligence(players, fps, frame_detections, cnn_events=None):

    print("\n================ GAME INTELLIGENCE START ================\n")

    hybrid_events = []
    prev_ball_position = None
    last_shot_frame = -9999
    SHOT_COOLDOWN = int(fps * 3)

    # -------- CNN EVENTS --------
    if cnn_events:
        print("🧠 CNN EVENTS RECEIVED:", len(cnn_events))
        for event in cnn_events:
            formatted = {
                "type": event["type"],
                "frame": event["frame"],
                "team": event.get("team", "unknown"),
                "zone": "unknown",
                "points": 0,
                "intensity": "medium"
            }
            hybrid_events.append(formatted)
            print("➡ CNN Event Added:", formatted)

    # -------- SPATIAL INTELLIGENCE --------
    for frame_data in frame_detections:

        frame = frame_data["frame"]
        ball = frame_data.get("ball")
        rim = frame_data.get("rim")
        players_frame = frame_data.get("players", [])
        segmentation = frame_data.get("segmentation", [])

        ball_speed = calculate_speed(prev_ball_position, ball)
        prev_ball_position = ball

        closest_player = find_closest_player(ball, players_frame)
        team = closest_player["team"] if closest_player else "unknown"

        zone = "unknown"

        if closest_player and segmentation:
            px, py = closest_player["center"]
            player_point = Point(px, py)

            for seg in segmentation:
                polygon = Polygon(seg["polygon"])
                if polygon.contains(player_point):
                    if seg["class"].lower() in ["three_point", "three point line"]:
                        zone = "three_point"
                    elif seg["class"].lower() in ["paint", "key"]:
                        zone = "paint"
                    else:
                        zone = seg["class"].lower()

        # -------- SHOT DETECTION --------
        if ball and rim:
            dist_to_rim = distance(ball, rim)

            if (
                dist_to_rim < 80
                and ball_speed > 15
                and frame - last_shot_frame > SHOT_COOLDOWN
            ):

                points = 3 if zone == "three_point" else 2

                event = {
                    "type": "shot",
                    "frame": frame,
                    "team": team,
                    "zone": zone,
                    "points": points,
                    "intensity": "high"
                }

                hybrid_events.append(event)
                print("🔥 Shot Event Detected:", event)

                last_shot_frame = frame

    print("\n🔥 TOTAL HYBRID EVENTS:", len(hybrid_events))
    print("=========================================================\n")

    return hybrid_events