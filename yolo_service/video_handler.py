# Gasby-Ai/Yolo_service/video_handler.py
import os
import cv2
import json
import torch
import numpy as np
from ultralytics import YOLO
from shapely.geometry import Point, Polygon

os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"

# -------------------------------------------------
# DEVICE SETUP
# -------------------------------------------------

if torch.cuda.is_available():
    DEVICE = "cuda"
elif torch.backends.mps.is_available():
    DEVICE = "mps"
else:
    DEVICE = "cpu"

print("🔥 YOLO Running On:", DEVICE)

# -------------------------------------------------
# LOAD MODELS
# -------------------------------------------------

detection_model = YOLO("resources/weights/detection/best.pt")
segmentation_model = YOLO("resources/weights/segmentation/best.pt")

detection_model.to(DEVICE)
segmentation_model.to(DEVICE)

print("📦 Detection Classes:", detection_model.names)
print("📦 Segmentation Classes:", segmentation_model.names)


# -------------------------------------------------
# COLOR MATCHING
# -------------------------------------------------

def closest_color(avg_bgr, team_colors):
    min_dist = float("inf")
    best_team = "unknown"

    for team_name, color_bgr in team_colors.items():
        dist = np.linalg.norm(np.array(avg_bgr) - np.array(color_bgr))
        if dist < min_dist:
            min_dist = dist
            best_team = team_name

    return best_team


# -------------------------------------------------
# VIDEO HANDLER
# -------------------------------------------------

class VideoHandler:

    def __init__(self, video, team_colors):
        self.video = video
        self.team_colors = team_colors

    def run_detectors(self, source):

        fps = self.video.get(cv2.CAP_PROP_FPS) or 30
        total_frames = int(self.video.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps

        FRAME_SKIP = 5 if duration < 60 else 10 if duration < 180 else 15

        frame_count = 0
        frame_level_data = []

        while self.video.isOpened():

            ret, frame = self.video.read()
            if not ret:
                break

            if frame_count % FRAME_SKIP != 0:
                frame_count += 1
                continue

            resized = cv2.resize(frame, (640, 640))

            # ----------------------------
            # 1️⃣ OBJECT DETECTION
            # ----------------------------

            det_results = detection_model.predict(
                resized,
                conf=0.25,
                verbose=False
            )[0]

            # ----------------------------
            # 2️⃣ SEGMENTATION
            # ----------------------------

            seg_results = segmentation_model.predict(
                resized,
                conf=0.25,
                verbose=False
            )[0]

            segmentation_data = []

            if seg_results.masks is not None:

                for mask_xy, box in zip(seg_results.masks.xy, seg_results.boxes):

                    cls = int(box.cls[0])
                    class_name = segmentation_model.names[cls]

                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()

                    segmentation_data.append({
                        "class": class_name,
                        "bbox": [float(x1), float(y1), float(x2), float(y2)],
                        "polygon": mask_xy.tolist()
                    })

            # ----------------------------
            # 3️⃣ PROCESS DETECTIONS
            # ----------------------------

            players = []
            ball = None
            rim = None

            if det_results.boxes is not None:

                for box in det_results.boxes:

                    cls = int(box.cls[0])
                    label = detection_model.names[cls].lower()

                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()

                    cx = (x1 + x2) / 2
                    cy = (y1 + y2) / 2

                    # FOOT POSITION (important for zone detection)
                    foot_point = Point(cx, y2)

                    # ----------------------------
                    # PLAYER
                    # ----------------------------

                    if "person" in label or "player" in label:

                        zone = "unknown"

                        for seg in segmentation_data:
                            polygon = Polygon(seg["polygon"])

                            if polygon.contains(foot_point):

                                if seg["class"] == "paint":
                                    zone = "paint"

                                elif seg["class"] == "three point line":
                                    zone = "three_point"

                                elif seg["class"] == "center-circle":
                                    zone = "center_circle"

                        crop = resized[int(y1):int(y2), int(x1):int(x2)]

                        if crop.size != 0:
                            avg_color = crop.mean(axis=(0, 1))
                            team = closest_color(avg_color, self.team_colors)
                        else:
                            team = "unknown"

                        players.append({
                            "center": [float(cx), float(cy)],
                            "bbox": [float(x1), float(y1), float(x2), float(y2)],
                            "team": team,
                            "zone": zone
                        })

                    # ----------------------------
                    # BALL
                    # ----------------------------

                    if "ball" in label:
                        ball = [float(cx), float(cy)]

                    # ----------------------------
                    # RIM
                    # ----------------------------

                    if "rim" in label or "basket" in label:
                        rim = [float(cx), float(cy)]

            # ----------------------------
            # SAVE FRAME DATA
            # ----------------------------

            frame_level_data.append({
                "frame": frame_count,
                "players": players,
                "ball": ball,
                "rim": rim,
                "segmentation": segmentation_data
            })

            frame_count += 1

        self.video.release()

        output_path = f"{source}/frame_level_detection.json"

        with open(output_path, "w") as f:
            json.dump(frame_level_data, f, indent=4)

        print("✅ Frame-level Detection Ready (With Segmentation JSON)")

        return frame_level_data