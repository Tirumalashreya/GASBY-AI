# service/commentary_engine.py


def group_events(action_data):
    """
    Groups consecutive frames with same player + same action
    and adds intensity to each grouped event
    """

    if not action_data:
        return []

    # Sort by frame
    action_data = sorted(action_data, key=lambda x: x["frame"])

    events = []

    current_event = {
        "player": action_data[0]["player"],
        "action": action_data[0]["action"],
        "team": action_data[0]["team"],
        "start_frame": action_data[0]["frame"],
        "end_frame": action_data[0]["frame"]
    }

    for entry in action_data[1:]:

        if (
            entry["player"] == current_event["player"]
            and entry["action"] == current_event["action"]
            and entry["frame"] == current_event["end_frame"] + 1
        ):
            # Extend current event
            current_event["end_frame"] = entry["frame"]
        else:
            events.append(current_event)

            current_event = {
                "player": entry["player"],
                "action": entry["action"],
                "team": entry["team"],
                "start_frame": entry["frame"],
                "end_frame": entry["frame"]
            }

    events.append(current_event)

    # Add intensity to each event
    for event in events:
        event["intensity"] = get_intensity(event["action"])

    return events


def get_intensity(action):
    """
    Returns intensity level based on action
    """

    high = ["shoot", "block"]
    medium = ["run", "ball in hand", "pass"]
    low = ["walk", "no_action"]

    if action in high:
        return "high"
    elif action in medium:
        return "medium"
    else:
        return "low"
