#Gasby-Ai/action_service/game_engine.py
def generate_score_timeline(events):

    score = {}
    timeline = []

    for event in events:

        team = event.get("team", "unknown")
        zone = event.get("zone", "unknown")

        if team not in score:
            score[team] = 0

        if event["type"] == "shot":

            if zone == "three_point":
                score[team] += 3
            else:
                score[team] += 2

        timeline.append({
            "frame": event["frame"],
            "score": score.copy()
        })

    return timeline