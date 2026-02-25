# Gasby-Ai/Yolo_service/player_tracking.py

import json
import numpy as np
import cv2
import math

MAX_DISTANCE = 80  # threshold for same player matching


class Player:
    def __init__(self, player_id, bbox):
        self.player_id = player_id
        self.bboxes = {}
        self.last_center = None


def calculate_center(box):
    x1, y1, x2, y2 = box
    return ((x1 + x2) / 2, (y1 + y2) / 2)


def distance(p1, p2):
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)


def match_player(existing_players, box, frame_index, next_id):

    center = calculate_center(box)

    best_match = None
    min_dist = float("inf")

    for player in existing_players:
        if player.last_center is None:
            continue

        d = distance(center, player.last_center)

        if d < min_dist and d < MAX_DISTANCE:
            min_dist = d
            best_match = player

    if best_match:
        best_match.bboxes[frame_index] = box
        best_match.last_center = center
        return best_match, next_id

    # New player
    new_player = Player(next_id, box)
    new_player.bboxes[frame_index] = box
    new_player.last_center = center
    existing_players.append(new_player)
    return new_player, next_id + 1


def player_tracking(source):

    with open(source + '/data.json') as f:
        frames = json.load(f)

    players = []
    next_id = 0
    output = []

    for frame_index, detections in enumerate(frames):

        for detection in detections:

            if detection.get("name") != "player":
                continue

            box = (
                detection["box"]["x1"],
                detection["box"]["y1"],
                detection["box"]["x2"],
                detection["box"]["y2"]
            )

            player, next_id = match_player(players, box, frame_index, next_id)

            output.append({
                "player_id": player.player_id,
                "frame": frame_index,
                "bbox": box
            })

    with open(source + '/tracked_players.json', 'w') as f:
        json.dump(output, f, indent=4)

    print("✅ Player tracking complete")
    return players