# Create_gifs.py for testing and inspection
import json
import os
from PIL import Image, ImageDraw
import cv2
import numpy as np

source = './video/b6a4e05c-13e6-4441-926c-c14d1abf0ffe'
# Load player positions from the JSON file
with open(source + '/player_positions_filtered.json', 'r') as file:
    player_positions = json.load(file)

# Path to the directory containing the images
image_dir = source + '/image'

# Path to the directory where the player GIFs will be saved
output_gif_dir = source + '/player_gifs'
os.makedirs(output_gif_dir, exist_ok=True)

# Function to draw a red dot on the image at the specified position
def draw_red_dot(image_path, position, position_name):
    with Image.open(image_path) as img:
        draw = ImageDraw.Draw(img)
        x, y = position
        radius = 5
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill='red')
        
        # PIL 이미지를 numpy 배열로 변환
        img_array = np.array(img)
        x_int, y_int = int(x), int(y - 10)
        
              # 라벨 작성
        label_text = f"{position_name}"
        cv2.putText(img_array, label_text, (x_int, y_int), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        
        # numpy 배열을 PIL 이미지로 다시 변환
        img_with_label = Image.fromarray(img_array)
        
        return img_with_label

# Generate GIFs for each player
for player in player_positions:
    player_id = player['player_id']
    positions = player['positions']
    
    frames = []
    for frame_data in positions:
        frame_number = frame_data['frame']
        position = frame_data['position']
        position_name = frame_data['position_name']
        
        image_path = os.path.join(image_dir, f'output_image{frame_number}.jpg')
        if os.path.exists(image_path):
            img_with_dot = draw_red_dot(image_path, position, position_name)
            frames.append(img_with_dot)
        else:
            print(f"Image {image_path} does not exist.")
    
    if frames:
        output_gif_path = os.path.join(output_gif_dir, f'player_{player_id}.gif')
        frames[0].save(output_gif_path, save_all=True, append_images=frames[1:], loop=0, duration=100)
        print(f"Saved GIF for player {player_id} at {output_gif_path}")
    else:
        print(f"No frames available for player {player_id}")