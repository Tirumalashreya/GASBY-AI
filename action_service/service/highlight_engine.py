# GASBY_Ai/action_service/service/highlight_engine.py

import os
import subprocess


def generate_highlights(video_path, events, fps, output_path):

    if not events:
        print("⚠ No events provided.")
        return None

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    highlight_ranges = []

    for event in events:

        event_type = event.get("type")
        frame = event.get("frame")
        intensity = event.get("intensity", "medium")
        points = event.get("points", 0)

        if frame is None:
            continue

        # 🎯 Only consider important events
        if event_type != "shot":
            continue

        center_sec = frame / fps

        # -----------------------
        # PRIORITY BASED WINDOW
        # -----------------------

        if points == 3:
            window = 6
        elif intensity == "high":
            window = 5
        else:
            window = 4

        start_sec = max(0, center_sec - window)
        end_sec = center_sec + window

        highlight_ranges.append((start_sec, end_sec))

    # -----------------------
    # FALLBACK IF NO SHOTS
    # -----------------------

    if not highlight_ranges:
        print("⚠ No shot highlights found. Using fallback first 20 seconds.")
        highlight_ranges = [(0, 20)]

    # -----------------------
    # MERGE OVERLAPS
    # -----------------------

    highlight_ranges.sort()
    merged = []

    for start, end in highlight_ranges:
        if not merged:
            merged.append([start, end])
        else:
            last = merged[-1]
            if start <= last[1]:
                last[1] = max(last[1], end)
            else:
                merged.append([start, end])

    temp_clips = []

    # -----------------------
    # EXTRACT CLIPS
    # -----------------------

    for idx, (start, end) in enumerate(merged):

        temp_clip = f"temp_clip_{idx}.mp4"

        subprocess.run([
            "ffmpeg", "-y",
            "-ss", str(start),
            "-to", str(end),
            "-i", video_path,
            "-c:v", "libx264",
            "-c:a", "aac",
            temp_clip
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        if os.path.exists(temp_clip):
            temp_clips.append(temp_clip)

    if not temp_clips:
        return None

    # -----------------------
    # CONCAT
    # -----------------------

    concat_file = "concat.txt"

    with open(concat_file, "w") as f:
        for clip in temp_clips:
            f.write(f"file '{clip}'\n")

    subprocess.run([
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", concat_file,
        "-c", "copy",
        output_path
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Cleanup
    for clip in temp_clips:
        os.remove(clip)

    os.remove(concat_file)

    return output_path if os.path.exists(output_path) else None