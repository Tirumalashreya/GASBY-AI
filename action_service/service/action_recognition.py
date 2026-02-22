from __future__ import print_function
import os
import cv2
import numpy as np
from easydict import EasyDict

import torch
import torch.nn as nn
from torchvision import models
from torchvision.models.video import R2Plus1D_18_Weights

from utils.checkpoints import load_weights


# =====================================================
# CONFIG
# =====================================================

args = EasyDict({

    # Action Recognition
    'base_model_name': 'r2plus1d_multiclass',
    'pretrained': False,  # 🔥 IMPORTANT: we load our own weights
    'lr': 0.0001,
    'start_epoch': 24,    # 🔥 MUST MATCH YOUR FILE NAME
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
        "9": "walk",
        "10": "discard"
    },

    'model_path': "model_checkpoints/r2plus1d_augmented-2/",
    'history_path': "histories/history_r2plus1d_augmented-2.txt",

    'seq_length': 16,
    'vid_stride': 8
})


# =====================================================
# VIDEO CROPPING
# =====================================================

def cropVideo(clip, crop_window, max_w, max_h):

    video = []

    for i, frame in enumerate(clip):

        x1 = int(crop_window[i][0])
        y1 = int(crop_window[i][1])
        x2 = int(crop_window[i][2])
        y2 = int(crop_window[i][3])

        cropped_frame = frame[y1:y2, x1:x2]

        try:
            resized_frame = cv2.resize(
                cropped_frame,
                (128, 176),
                interpolation=cv2.INTER_NEAREST
            )
        except:
            resized_frame = np.zeros((176, 128, 3), dtype=np.uint8)

        video.append(resized_frame)

    return video


def cropWindows(vidFrames, players, seq_length=16, vid_stride=8):

    player_frames = {}

    for p_idx, player in enumerate(players):

        player_frames[p_idx] = []

        bbox_items = list(player.bboxs.items())

        if len(bbox_items) < seq_length:
            continue

        for clip_start in range(0, len(bbox_items) - seq_length + 1, vid_stride):

            clip_boxes = bbox_items[clip_start: clip_start + seq_length]

            frame_indices = [f[0] for f in clip_boxes]

            if frame_indices[-1] >= len(vidFrames):
                continue

            clip_frames = vidFrames[
                frame_indices[0]: frame_indices[-1] + 1
            ]

            crop_boxes = [f[1] for f in clip_boxes]

            cropped_video = cropVideo(
                clip_frames,
                crop_boxes,
                0,
                0
            )

            if len(cropped_video) == seq_length:
                player_frames[p_idx].append(cropped_video)

    return player_frames


# =====================================================
# INFERENCE
# =====================================================

def inference_batch(batch):
    return batch.permute(0, 4, 1, 2, 3)


def ActioRecognition(videoFrames, players):

    frames = cropWindows(
        videoFrames,
        players,
        seq_length=args.seq_length,
        vid_stride=args.vid_stride
    )

    if not frames:
        return players, {}

    print("Number of players tracked:", len(frames))

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # 🔥 Load model WITHOUT downloading pretrained weights
    model = models.video.r2plus1d_18(weights=None)

    num_ftrs = model.fc.in_features
    model.fc = nn.Linear(num_ftrs, args.num_classes)

    # 🔥 Load your trained weights
    model = load_weights(model, args)

    model = model.to(device)
    model.eval()

    predictions = {}
    drop_list = []

    for p_id, player in enumerate(players):

        if p_id not in frames or len(frames[p_id]) == 0:
            drop_list.append(p_id)
            continue

        input_frames_np = np.array(frames[p_id])

        input_tensor = torch.tensor(
            input_frames_np,
            dtype=torch.float
        ).to(device)

        input_tensor = inference_batch(input_tensor)

        with torch.no_grad():
            outputs = model(input_tensor)
            _, preds = torch.max(outputs, 1)

        predictions[p_id] = preds.cpu().numpy().tolist()

    for p_id in reversed(drop_list):
        players.pop(p_id)

    print("Predictions:", predictions)

    return players, predictions


# =====================================================
# JSON CREATION
# =====================================================

def create_json(players, actions, frame_len):

    json_list = []

    player_frames = [list(player.bboxs.keys()) for player in players]

    for frame in range(frame_len):
        for p_idx in range(len(players)):
            if frame in player_frames[p_idx]:
                json_list.append({
                    'player': players[p_idx].ID,
                    'frame': frame,
                    'team': players[p_idx].team,
                    'position': players[p_idx].positions[frame],
                    'action': players[p_idx].actions.get(frame, "unknown")
                })

    return json_list
