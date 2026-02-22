#Gasby-flask/video_handler.py
import os
import cv2
import json
from ultralytics import YOLO
from player_tracking import player_tracking
from shapely.geometry import Point, Polygon

# =========================
# MODEL PATHS
# =========================

detection_model_path = "resources/weights/detection/best.pt"
segmentation_model_path = "resources/weights/segmentation/best.pt"

detection_model = YOLO(detection_model_path)
segmentation_model = YOLO(segmentation_model_path)


def detect_objects(image, model):
    results = model.predict(source=image, verbose=False)
    return json.loads(results[0].tojson())


def save_list_to_json(data, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


class VideoHandler:

    def __init__(self, video, frame_skip=1):
        self.video = video
        self.frames = []
        self.frame_skip = frame_skip

    def run_detectors(self, source, teamA, teamB):

        os.makedirs(source + "/image", exist_ok=True)

        frame_count = 0
        image_index = 0

        while self.video.isOpened():

            ret, frame = self.video.read()
            if not ret:
                break

            if frame_count % self.frame_skip == 0:

                detections = detect_objects(frame, detection_model)
                cleaned = []

                if len(detections) != 0:

                    segmentations = detect_objects(frame, segmentation_model)
                    detections = self.check_detection_in_segmentation(
                        detections, segmentations
                    )

                    for det in detections:

                        box = det["box"]

                        cleaned.append({
                            "name": det.get("name"),
                            "confidence": float(det.get("confidence", 0)),
                            "box": {
                                "x1": float(box["x1"]),
                                "y1": float(box["y1"]),
                                "x2": float(box["x2"]),
                                "y2": float(box["y2"]),
                            },
                            "uniform_color": None,
                            "position_name": det.get("position_name")
                        })

                self.frames.append(cleaned)

                cv2.imwrite(
                    f"{source}/image/output_image{image_index}.jpg",
                    frame
                )
                image_index += 1

            frame_count += 1

        save_list_to_json(self.frames, source + "/data.json")

        player_tracking(source, teamA, teamB)

    def check_detection_in_segmentation(self, detections, segmentations):

        new_detection = []

        for detection in detections:

            if detection["name"] != "basketball":

                box = detection["box"]

                center_x = float((box["x1"] + box["x2"]) / 2)
                center_y = float(box["y2"])

                center_point = Point(center_x, center_y)

                for segmentation in segmentations:

                    if "segments" not in segmentation:
                        continue

                    seg_x = segmentation["segments"].get("x")
                    seg_y = segmentation["segments"].get("y")

                    if not seg_x or not seg_y:
                        continue

                    polygon_points = list(
                        zip([float(x) for x in seg_x],
                            [float(y) for y in seg_y])
                    )

                    polygon = Polygon(polygon_points)

                    if polygon.contains(center_point):
                        detection["position_name"] = segmentation["name"]
                        new_detection.append(detection)
                        break

            else:
                new_detection.append(detection)

        return new_detection
