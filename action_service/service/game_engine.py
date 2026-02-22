def generate_score_timeline(events):

    score = {}
    timeline = []

    for event in events:

        team = event.get("team", "unknown")

        if team not in score:
            score[team] = 0

        if event["action"] == "shoot":
            score[team] += 2  # assume 2 points

        timeline.append({
            "frame": event["end_frame"],
            "score": score.copy()
        })

    return timeline


def build_drawtext_filter(score_timeline, fps):

    filters = []

    for entry in score_timeline:

        frame = entry["frame"]
        score = entry["score"]

        time_sec = frame / fps

        text = " | ".join([f"{team}: {pts}" for team, pts in score.items()])

        filters.append(
            f"drawtext=text='{text}':"
            f"x=50:y=50:"
            f"fontsize=40:"
            f"fontcolor=white:"
            f"box=1:boxcolor=black@0.6:"
            f"enable='gte(t,{time_sec})'"
        )

    return ",".join(filters)
