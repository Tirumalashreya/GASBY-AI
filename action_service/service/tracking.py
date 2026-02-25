#action_service/service/tracking.py
import math

IOU_THRESHOLD = 0.3


class TrackedPlayer:
    def __init__(self, player_id):
        self.id = player_id
        self.bboxes = {}
        self.last_bbox = None


def compute_iou(boxA, boxB):

    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])

    interArea = max(0, xB - xA) * max(0, yB - yA)

    boxAArea = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
    boxBArea = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])

    return interArea / float(boxAArea + boxBArea - interArea + 1e-6)


def build_tracks(frame_data):

    players = []
    next_id = 0

    for frame in frame_data:

        frame_number = frame["frame"]

        for p in frame.get("players", []):

            bbox = p["bbox"]

            best_match = None
            best_iou = 0

            for player in players:

                if player.last_bbox is None:
                    continue

                iou = compute_iou(bbox, player.last_bbox)

                if iou > best_iou and iou > IOU_THRESHOLD:
                    best_iou = iou
                    best_match = player

            if best_match:
                best_match.bboxes[frame_number] = bbox
                best_match.last_bbox = bbox
            else:
                new_player = TrackedPlayer(next_id)
                new_player.bboxes[frame_number] = bbox
                new_player.last_bbox = bbox
                players.append(new_player)
                next_id += 1

    print("✅ IoU Tracking complete. Players:", len(players))
    return players