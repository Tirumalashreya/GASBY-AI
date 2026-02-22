# GASBY Action Recognition Service - AI Agent Instructions

## Architecture Overview
This is a Flask-based action recognition service for sports video analysis using R2+1D deep learning models. The service processes uploaded videos by:
1. Downloading video, player tracking (MOT), and ball tracking data from AWS S3
2. Extracting player bounding box sequences from tracking data
3. Cropping and resizing player clips to 176x128 for model input
4. Running R2+1D inference on 16-frame sequences with 8-frame stride
5. Post-processing actions based on ball possession logic
6. Uploading JSON results back to S3

**Key Components:**
- `app.py`: Flask routes and main processing pipeline
- `service/action_recognition.py`: Core ML inference and video cropping logic
- `entity/player.py`: Player data model with bboxs/actions keyed by frame number
- `utils/s3utils.py`: AWS S3 download/upload utilities
- `utils/checkpoints.py`: PyTorch model weight loading

## Critical Workflows
- **Local Development**: Run `python3 app.py` to start Flask dev server on port 5000
- **Model Setup**: Place trained `.pt` files in `model_checkpoints/r2plus1d_augmented-2/` (current: `r2plus1d_multiclass_24_0.0001.pt`)
- **Environment**: Create `.env` with `AWS_Accesskey`, `AWS_Secretkey`, `AWS_Region` (note inconsistent naming with standard AWS env vars)
- **Data Flow**: POST to `/action-predict/predict` with `{"uuid": "session-id"}` triggers full pipeline

## Project-Specific Patterns
- **Player Data Structure**: Use `Player` objects with dicts for `bboxs`, `positions`, `actions` keyed by frame int (e.g., `player.actions[frame_num] = "run"`)
- **Action Prediction**: Models predict on 16-frame clips; assign predictions to frames using `action_idx = j // 8` logic
- **Ball Possession Logic**: Adjust non-ball-handler actions (e.g., change "dribble" to "run" for other players)
- **Video Processing**: Resize cropped frames to (176, 128) for R2+1D input; handle variable bbox sizes
- **S3 Buckets**: `gasby-req123` (videos), `gasby-mot-result1` (tracking), `gasby-actrecog-result1` (results)
- **Action Labels**: 11-class mapping from `args.labels` in `action_recognition.py` (e.g., "8" -> "no_action", "9" -> "walk")
- **Temporary Directories**: Create `resources/{uuid}/` for downloads, `outputs/{uuid}/` for results; always clean up with `shutil.rmtree()`

## Integration Points
- **AWS S3**: All I/O via boto3; bucket/folder structure critical for data retrieval
- **MOT Format**: Tracking data as JSON with player_id, team, positions array containing frame/box/position_name
- **Model Dependencies**: R2+1D from torchvision; custom FC layer for 11 classes
- **CORS**: Enabled for cross-origin requests in production

## Common Pitfalls
- Frame indexing: Ensure frame numbers match between video, tracking, and action assignments
- Bbox format: Convert to (x1,y1,x2,y2) for cropping; handle empty/invalid bboxes
- Memory usage: Process videos frame-by-frame; avoid loading entire video at once
- Action assignment: Use clip-based prediction with stride logic; don't assign actions to frames without bboxes</content>
<parameter name="filePath">/Users/vyju/GASBY-Action-Recognition/.github/copilot-instructions.md