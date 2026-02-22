**Repo Overview**
- **Purpose:** Flask server that runs YOLOv8 pipelines (detection, segmentation, uniform classification) on uploaded game videos and uploads processed outputs to S3.
- **Key entrypoints:** [app.py](app.py#L1-L200) handles HTTP API and S3 interaction; [video_handler.py](video_handler.py#L1-L400) runs YOLO models and produces `data.json`.

**Architecture & Dataflow**
- **Upload trigger -> app.py**: POST `/yolo-predict/upload` expects a JSON body with `payload` equal to an S3 folder prefix. The handler lists objects under that prefix in the `gasby-reqs` bucket, downloads a `.mp4` and a metadata `.json`, then runs detection and uploads results to `gasby-mot-resultss` (see [app.py](app.py#L1-L200)).
- **Video processing:** `yolo_detection()` opens the local video and creates `VideoHandler` which calls `run_detectors()` to: frame-scan, detect (detection_model), segment (segmentation_model), classify uniform color (classify_model), save per-frame images and `data.json` (see [video_handler.py](video_handler.py#L1-L400)).
- **Post-processing files:** `player_tracking.py` consumes `data.json` and emits `tracked_results.json` and `ball.json`. `json_convert.py` further converts tracked JSON into the final upload format. Check these files for tracking and conversion logic.

**Important conventions & expectations (concrete)**
- **S3 layout:** incoming folder (payload) must contain exactly one `.mp4` and one metadata `.json`. Example: `payload/video.mp4` and `payload/meta.json`.
- **Metadata keys:** app expects `team_a_color` and `team_b_color` inside the downloaded JSON (see [app.py](app.py#L1-L200)).
- **Local workspace:** app downloads to `./video/{payload}` and writes `image/`, `data.json`, `ball.json`, and `player_positions_filtered.json` there before upload.
- **Output names:** uploaded outputs are `payload/payload_ball.json` and `payload/payload.json` (note the result bucket in code is `gasby-mot-resultss` — double-check spelling if uploads fail).

**Runtime & env**
- **Env variables used:** `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION` are read from `.env` by `dotenv_values('.env')` in [app.py](app.py#L1-L200). The README lists different keys — use the code's names.
- **Run locally:** `flask run --port 5000` or `python3 app.py`. The service exposes `/yolo-predict` (GET health) and `/yolo-predict/upload` (POST).
- **Python deps:** check [requirements.txt](requirements.txt) before running; YOLO/Ultralytics model loading is heavy and done at import-time in `video_handler.py`.

**Agent-specific guidance (how to be productive quickly)**
- **Avoid reloading models:** `video_handler.py` constructs YOLO objects at module import (detection_model, segmentation_model, classify_model). Do not re-initialize these per-request; use the top-level objects or refactor to lazy-load if needed for tests.
- **S3 credentials & permissions:** tests and local runs require valid AWS keys and permission to `gasby-reqs` and `gasby-mot-resultss`. If you don't have access, mock `boto3.client` or run against a local S3-compatible test bucket.
- **Data invariants:** expect camera frames to be processed sequentially and `list` (in `video_handler.py`) to contain detections per frame (non-thread-safe global — be cautious when parallelizing runs).
- **Model artifacts path:** models live in `resources/weights/{detection,segmentation,classify}/best.pt`. Use these paths when updating or replacing models.

**Examples (use these when generating tests or automation)**
- Example POST body for upload: `{ "payload": "test-folder" }`. The app will look under `gasby-reqs` for `test-folder/` (see [app.py](app.py#L1-L200)).
- Expected metadata JSON shape (minimal): `{ "team_a_color": "red", "team_b_color": "blue" }`.

**Working with code changes**
- If modifying model loading or inference, update `video_handler.py` and keep inference functions deterministic: `detect_objects()`, `classify_uniform_color()` and `check_detection_in_segmentation()` are the core helpers.
- When changing any filename conventions (local or S3), update both `app.py` upload/download logic and downstream consumers (`player_tracking.py`, `json_convert.py`).

**Troubleshooting quick checks**
- If uploads fail, verify `.env` names and that the result bucket name in code (`gasby-mot-resultss`) is correct.
- If processing stalls, check that YOLO models are loading successfully at import (can take significant time and memory) and that `cv2.VideoCapture` opened the file successfully.

If anything above is unclear or you want the agent to include extra examples (unit tests, CI steps, or a refactor to lazy-load models), tell me what to add and I will iterate.
