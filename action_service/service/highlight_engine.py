# service/highlight_engine.py
import os
import subprocess


def generate_highlights(video_path, events, fps, output_path):

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    highlight_ranges = []

    for event in events:
        if event.get("intensity") == "high":

            start_sec = max(0, event["start_frame"] / fps - 2)
            end_sec = event["end_frame"] / fps + 2

            highlight_ranges.append((start_sec, end_sec))

    if not highlight_ranges:
        return None

    temp_clips = []

    for idx, (start, end) in enumerate(highlight_ranges):

        temp_clip = f"temp_clip_{idx}.mp4"

        command = [
            "ffmpeg",
            "-y",
            "-i", video_path,
            "-ss", str(start),
            "-to", str(end),
            "-c", "copy",
            temp_clip
        ]

        subprocess.run(command)
        temp_clips.append(temp_clip)

    with open("concat.txt", "w") as f:
        for clip in temp_clips:
            f.write(f"file '{clip}'\n")

    subprocess.run([
        "ffmpeg",
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", "concat.txt",
        "-c", "copy",
        output_path
    ])

    for clip in temp_clips:
        os.remove(clip)

    os.remove("concat.txt")

    return output_path
