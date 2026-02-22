#json_convert.py

import json
from collections import defaultdict, Counter

def calculate_center_position(box):
    """Calculate the center position of a bounding box."""
    x_center = (box[0] + box[2]) / 2
    y_center = (box[1] + box[3]) / 2
    return [x_center, y_center]

def process_tracked_data(tracked_data, teamA, teamB):
    """Process tracked data to categorize by player_id and calculate positions."""
    player_positions = defaultdict(lambda: {'player_id': None, 'positions': [], 'uniform_colors': []})

    for frame_number, frame_data in enumerate(tracked_data):
        for player in frame_data:
            player_id = player['player_id']
            position = calculate_center_position(player['box'])
            if player_positions[player_id]['player_id'] is None:
                player_positions[player_id]['player_id'] = player_id
            player_positions[player_id]['positions'].append({
                'frame': frame_number,
                'position': position,
                'box': player['box'],
                'position_name': player['position_name'],
                'uniform_color': player['uniform_color']
            })
            player_positions[player_id]['uniform_colors'].append(player['uniform_color'])

    # Filter out players with positions less than or equal to 20 frames
    filtered_player_positions = [
        {
            'player_id': player_id,
            'team': 'A' if Counter(data['uniform_colors']).most_common(1)[0][0] == teamA else 'B',
            'positions': data['positions']
        }
        for player_id, data in player_positions.items()
        if len(data['positions']) > 20
    ]

    return filtered_player_positions

def json_convert(source, teamA, teamB):
    # Load the tracked results data from the file
    file_path = f'{source}/tracked_results.json'
    with open(file_path, 'r') as file:
        tracked_data = json.load(file)

    # Process the tracked data
    filtered_player_positions = process_tracked_data(tracked_data, teamA, teamB)

    # Save the filtered result to a new JSON file
    output_file_path = f'{source}/player_positions_filtered.json'
    with open(output_file_path, 'w') as output_file:
        json.dump(filtered_player_positions, output_file, indent=4)

    print(f'Filtered data saved to {output_file_path}')

