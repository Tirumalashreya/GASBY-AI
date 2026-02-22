import json
import numpy as np
import cv2
import math
from scipy.optimize import linear_sum_assignment
from json_convert import json_convert


class KalmanFilter:
    def __init__(self):
        self.kalman = cv2.KalmanFilter(4, 2)
        self.kalman.measurementMatrix = np.array([[1, 0, 0, 0], [0, 1, 0, 0]], np.float32)
        self.kalman.transitionMatrix = np.array([[1, 0, 1, 0], [0, 1, 0, 1],
                                                 [0, 0, 1, 0], [0, 0, 0, 1]], np.float32)
        self.kalman.processNoiseCov = np.eye(4, dtype=np.float32) * 0.03
        self.kalman.measurementNoiseCov = np.eye(2, dtype=np.float32)

    def predict(self):
        pred = self.kalman.predict()
        return pred[0], pred[1]

    def correct(self, x, y):
        measurement = np.array([[np.float32(x)], [np.float32(y)]])
        self.kalman.correct(measurement)


class Player:
    def __init__(self, player_id, initial_position, bbox, position_name, uniform_color):
        self.player_id = player_id
        self.kalman_filter = KalmanFilter()
        self.kalman_filter.correct(initial_position[0], initial_position[1])
        self.position = initial_position
        self.position_name = position_name
        self.bbox = bbox
        self.uniform_color = uniform_color
        self.missed_frames = 0


def calculate_distance(x1, y1, x2, y2):
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


def get_player_positions(detections):

    positions = []
    bboxes = []
    position_names = []
    uniform_colors = []
    basketball_positions = []

    for detection in detections:

        if detection['name'] == 'player' and detection['confidence'] > 0.5:

            box = detection['box']
            x_center = (box['x1'] + box['x2']) / 2
            y_center = (box['y1'] + box['y2']) / 2

            positions.append((x_center, y_center))
            bboxes.append((box['x1'], box['y1'], box['x2'], box['y2']))
            position_names.append(detection.get('position_name'))
            uniform_colors.append(detection.get('uniform_color'))

        elif detection['name'] == 'basketball':

            box = detection['box']
            x_center = (box['x1'] + box['x2']) / 2
            y_center = (box['y1'] + box['y2']) / 2

            basketball_positions.append({
                "basketball": detection,
                "center": (x_center, y_center)
            })

    # SAFE basketball matching
    for basketball in basketball_positions:

        if len(positions) == 0:
            continue

        min_dis = float("inf")
        min_ind = -1

        for i, position in enumerate(positions):

            dis = calculate_distance(
                position[0], position[1],
                basketball['center'][0], basketball['center'][1]
            )

            if dis < min_dis:
                min_dis = dis
                min_ind = i

        if min_ind != -1:
            basketball['player_bbox'] = bboxes[min_ind]
            basketball['dis'] = min_dis

    return positions, bboxes, position_names, uniform_colors, basketball_positions


def compute_iou(boxA, boxB):
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])

    interArea = max(0, xB - xA + 1) * max(0, yB - yA + 1)

    boxAArea = (boxA[2] - boxA[0] + 1) * (boxA[3] - boxA[1] + 1)
    boxBArea = (boxB[2] - boxB[0] + 1) * (boxB[3] - boxB[1] + 1)

    if boxAArea + boxBArea - interArea == 0:
        return 0

    return interArea / float(boxAArea + boxBArea - interArea)


def match_players(predicted_positions, curr_bboxes):

    if len(predicted_positions) == 0 or len(curr_bboxes) == 0:
        return [], [], None

    cost_matrix = np.zeros((len(predicted_positions), len(curr_bboxes)))

    for i, pred in enumerate(predicted_positions):
        for j, curr in enumerate(curr_bboxes):
            cost_matrix[i, j] = -compute_iou(pred, curr)

    row_ind, col_ind = linear_sum_assignment(cost_matrix)

    return row_ind, col_ind, cost_matrix


MAX_MISSED_FRAMES = 5


def track_players(players, player_id_counter,
                  curr_positions, curr_bboxes,
                  position_names, uniform_colors):

    if not players:

        for pos, bbox, name, color in zip(
                curr_positions, curr_bboxes,
                position_names, uniform_colors):

            players.append(Player(player_id_counter, pos, bbox, name, color))
            player_id_counter += 1

    else:

        row_ind, col_ind, cost_matrix = match_players(
            [p.bbox for p in players],
            curr_bboxes
        )

        assigned = set()

        for r, c in zip(row_ind, col_ind):

            if cost_matrix is not None and -cost_matrix[r, c] > 0.3:

                players[r].kalman_filter.correct(
                    curr_positions[c][0],
                    curr_positions[c][1]
                )

                players[r].position = curr_positions[c]
                players[r].bbox = curr_bboxes[c]
                players[r].missed_frames = 0
                players[r].position_name = position_names[c]
                players[r].uniform_color = uniform_colors[c]

                assigned.add(c)

        for i, (pos, bbox, name, color) in enumerate(
                zip(curr_positions, curr_bboxes,
                    position_names, uniform_colors)):

            if i not in assigned:
                players.append(Player(player_id_counter, pos, bbox, name, color))
                player_id_counter += 1

        for player in players:
            player.missed_frames += 1

        players[:] = [
            p for p in players
            if p.missed_frames <= MAX_MISSED_FRAMES
        ]

    return player_id_counter


def player_tracking(source, teamA, teamB):

    with open(source + '/data.json') as f:
        frames = json.load(f)

    tracked_results = []
    ball_results = []
    players = []
    player_id_counter = 0

    for frame_index, frame_data in enumerate(frames):

        curr_positions, curr_bboxes, names, colors, basketball_positions = \
            get_player_positions(frame_data)

        player_id_counter = track_players(
            players, player_id_counter,
            curr_positions, curr_bboxes,
            names, colors
        )

        frame_results = []

        for player in players:

            frame_results.append({
                'player_id': player.player_id,
                'position_name': player.position_name,
                'position': player.position,
                'box': player.bbox,
                'uniform_color': player.uniform_color
            })

            for basketball in basketball_positions:

                if basketball.get('player_bbox') == player.bbox:
                    ball_results.append({
                        'player_id': player.player_id,
                        'ball': basketball['basketball'],
                        'dis': basketball.get('dis'),
                        'frame': frame_index
                    })

        tracked_results.append(frame_results)

    with open(source + '/tracked_results.json', 'w') as f:
        json.dump(tracked_results, f, indent=4)

    with open(source + '/ball.json', 'w') as f:
        json.dump(ball_results, f, indent=4)

    json_convert(source, teamA, teamB)
