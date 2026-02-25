# Gasby-Ai/action_service/service/action_recognition.py

# Gasby-Ai/action_service/service/action_recognition.py

from __future__ import print_function
import numpy as np
import cv2
from easydict import EasyDict
import torch
import torch.nn as nn
from torchvision import models
from utils.checkpoints import load_weights


# =====================================================
# CONFIG
# =====================================================

args = EasyDict({

    'base_model_name': 'r2plus1d_multiclass',
    'start_epoch': 24,
    'lr': 0.0001,

    'num_classes': 10,

    'labels': {
        "0": "block",
        "1": "pass",
        "2": "run",
        "3": "dribble",
        "4": "shoot",
        "5": "ball in hand",
        "6": "defense",
        "7": "pick",
        "8": "no_action",
        "9": "walk"
    },

    'model_path': "model_checkpoints/r2plus1d_augmented-2/",

    # 🔥 Increased stride for speed
    'seq_length': 8,
    'vid_stride': 16   # was 8 → now 16 (2x faster)
})


# =====================================================
# LOAD MODEL
# =====================================================

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

print("🔥 Loading 3D CNN Action Model...")

ACTION_MODEL = models.video.r2plus1d_18(weights=None)

num_ftrs = ACTION_MODEL.fc.in_features
ACTION_MODEL.fc = nn.Linear(num_ftrs, args.num_classes)

ACTION_MODEL = load_weights(ACTION_MODEL, args)
ACTION_MODEL = ACTION_MODEL.to(device)
ACTION_MODEL.eval()

print("✅ 3D CNN Ready")


# =====================================================
# SAFE CROP
# =====================================================

def cropVideo(clip, crop_window):

    processed = []

    min_len = min(len(clip), len(crop_window))

    for i in range(min_len):

        frame = clip[i]
        h, w, _ = frame.shape

        try:
            x1, y1, x2, y2 = map(int, crop_window[i])
        except:
            processed.append(np.zeros((176, 128, 3), dtype=np.uint8))
            continue

        x1 = max(0, min(x1, w - 1))
        x2 = max(0, min(x2, w - 1))
        y1 = max(0, min(y1, h - 1))
        y2 = max(0, min(y2, h - 1))

        if x2 <= x1 or y2 <= y1:
            resized = np.zeros((176, 128, 3), dtype=np.uint8)
        else:
            cropped = frame[y1:y2, x1:x2]
            resized = cv2.resize(cropped, (128, 176))

        processed.append(resized)

    return processed


# =====================================================
# OPTIMIZED 3D CNN PIPELINE
# =====================================================

def run_action_recognition(videoFrames, tracked_players):

    print("🎯 Running Optimized 3D CNN Action Recognition...")

    cnn_events = []

    for player in tracked_players:

        bbox_items = sorted(player.bboxes.items())

        # 🔥 Skip very short tracks
        if len(bbox_items) < args.seq_length:
            continue

        for start in range(0, len(bbox_items) - args.seq_length + 1, args.vid_stride):

            clip_boxes = bbox_items[start:start + args.seq_length]
            frame_indices = [f[0] for f in clip_boxes]

            clip_frames = []
            for idx in frame_indices:
                if idx < len(videoFrames):
                    clip_frames.append(videoFrames[idx])

            if len(clip_frames) != args.seq_length:
                continue

            crop_boxes = [f[1] for f in clip_boxes]
            cropped = cropVideo(clip_frames, crop_boxes)

            if len(cropped) != args.seq_length:
                continue

            input_array = np.array(cropped, dtype=np.float32) / 255.0
            input_tensor = torch.tensor(input_array).unsqueeze(0)
            input_tensor = input_tensor.permute(0, 4, 1, 2, 3).to(device)

            with torch.no_grad():
                output = ACTION_MODEL(input_tensor)
                _, pred = torch.max(output, 1)

            action_label = args.labels.get(str(pred.item()), "unknown")

            if action_label not in ["no_action", "unknown"]:

                cnn_events.append({
                    "type": action_label,
                    "frame": frame_indices[0],
                    "team": getattr(player, "team", "unknown"),
                    "source": "cnn"
                })

    print("🔥 CNN Events:", len(cnn_events))
    return cnn_events