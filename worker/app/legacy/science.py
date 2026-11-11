import shutil
from app import fonts
import os
import sys
import subprocess
import asyncio
from app import tts_compat as edge_tts
from PIL import Image, ImageDraw, ImageFont
from mutagen.mp3 import MP3
import math

WIDTH, HEIGHT = 1280, 720
BG_COLOR = (20, 30, 40)
DEF_BG_COLOR = (30, 40, 55)  # Slightly lighter blue/grey for the definition area
FFMPEG_PATH = shutil.which("ffmpeg") or "ffmpeg"

os.makedirs("temp_frames", exist_ok=True)

async def generate_audio(text, filename):
    communicate = edge_tts.Communicate(text, "en-US-ChristopherNeural")
    await communicate.save(filename)
    return MP3(filename).info.length

def draw_dynamic_box(draw, center_x, center_y, text, font, text_color, bg_color, border_color):
    bbox = draw.textbbox((0, 0), text, font=font)
    padding_x, padding_y = 25, 12
    box_width = (bbox[2] - bbox[0]) + (padding_x * 2)
    box_height = (bbox[3] - bbox[1]) + (padding_y * 2)
    
    x0, y0 = center_x - (box_width / 2), center_y - (box_height / 2)
    x1, y1 = center_x + (box_width / 2), center_y + (box_height / 2)
    
    draw.rectangle([x0, y0, x1, y1], fill=bg_color, outline=border_color, width=3)
    draw.text((center_x, center_y), text, font=font, fill=text_color, anchor="mm")

def draw_scene_frame(car_x, wheel_angle, time_str, distance_km, filename):
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)
    
    # 1. Draw the Road
    draw.rectangle([0, 480, WIDTH, 600], fill=(50, 50, 50))
    
    # 2. Draw Milestones (0 to 20 km)
    pixels_per_km = 55
    start_x = 100
    for km in range(0, 25, 5):
        km_x = start_x + (km * pixels_per_km)
        if 0 <= km_x <= WIDTH:
            draw.rectangle([km_x, 480, km_x + 5, 520], fill=(255, 255, 0))
            font_km = fonts.truetype("arialbd.ttf", 30)
            draw.text((km_x, 530), f"{km} km", font=font_km, fill=(255, 255, 0), anchor="ma")

    # 3. Draw the Car
    car_y = 380 
    draw.rectangle([car_x, car_y + 30, car_x + 160, car_y + 100], fill=(220, 40, 40))
    draw.polygon([(car_x + 40, car_y + 30), (car_x + 60, car_y - 10), (car_x + 120, car_y - 10), (car_x + 130, car_y + 30)], fill=(220, 40, 40))
    draw.polygon([(car_x + 50, car_y + 25), (car_x + 65, car_y - 5), (car_x + 90, car_y - 5), (car_x + 90, car_y + 25)], fill=(200, 230, 255))
    draw.polygon([(car_x + 95, car_y + 25), (car_x + 95, car_y - 5), (car_x + 115, car_y - 5), (car_x + 125, car_y + 25)], fill=(200, 230, 255))
    draw.rectangle([car_x + 155, car_y + 60, car_x + 160, car_y + 80], fill=(255, 255, 0))

    # Wheels
    for wx in [car_x + 30, car_x + 120]:
        draw.ellipse([wx, car_y + 80, wx + 40, car_y + 120], fill=(0, 0, 0))
        draw.ellipse([wx + 10, car_y + 90, wx + 30, car_y + 110], fill=(200, 200, 200))
        cx, cy = wx + 20, car_y + 100
        for angle in [0, 90, 180, 270]:
            rad = math.radians(angle + wheel_angle)
            draw.line([cx, cy, cx + 10 * math.cos(rad), cy + 10 * math.sin(rad)], fill=(50, 50, 50), width=3)

    # 4. Draw UI Data Boxes
    font_bold = fonts.truetype("arialbd.ttf", 40)
    font_regular = fonts.truetype("arial.ttf", 40)
    font_time = fonts.truetype("arialbd.ttf", 35) 
    
    # Distance Box
    dist_text = f"Distance: {distance_km:.1f} km"
    draw_dynamic_box(draw, WIDTH - 220, 75, dist_text, font_bold, (0, 255, 0), (40, 50, 60), (0, 255, 0))

    # Time Box (Below the car)
    time_text = f"Time: {time_str}"
    draw_dynamic_box(draw, car_x + 80, 555, time_text, font_time, (255, 255, 255), (40, 50, 60), (255, 255, 255))

    # Center Text
    y_offset = 140
    text_lines = [
        "Uniform Speed",
        "Covering exactly 5 km every 1 hour",
        "Speed = 5 km / 1 h = 5 km/h"
    ]
    for i, line in enumerate(text_lines):
        f = font_bold if i == 0 else font_regular
        color = (255, 255, 255) if i == 0 else (255, 200, 0)
        draw.text((WIDTH // 2, y_offset), line, font=f, fill=color, anchor="ma")
        y_offset += 60

    # 5. Draw Definition Panel at the bottom
    draw.rectangle([0, 600, WIDTH, HEIGHT], fill=DEF_BG_COLOR)
    font_def_title = fonts.truetype("arialbd.ttf", 24)
    font_def_text = fonts.truetype("arial.ttf", 22)
    
    # Definition Title
    draw.text((40, 615), "Definitions:", font=font_def_title, fill=(255, 255, 255))
    
    # Definitions
    defs = [
        "• Speed: The rate of change of distance with respect to time.",
        "• Uniform Speed: When an object covers equal distances in equal intervals of time."
    ]
    y_def = 650
    for d in defs:
        draw.text((40, y_def), d, font=font_def_text, fill=(200, 200, 200))
        y_def += 30
        
    img.save(filename)

def main():
    voice_text = "Uniform speed means covering equal distances in equal intervals of time. Look at the time box below the car. The car covers exactly 5 kilometers every hour. Since the speed is constant, the time resets to zero after every 5 kilometers, while the distance keeps increasing."
    audio_file = "temp_frames/science_audio.mp3"
    duration = asyncio.run(generate_audio(voice_text, audio_file))
    
    print(f"Generating {duration:.2f} seconds of animation...")
    fps = 24
    total_frames = int(duration * fps)
    
    total_distance_km = 20.0
    
    for i in range(total_frames):
        time_elapsed = i / fps
        progress = time_elapsed / duration
        
        distance_km = progress * total_distance_km
        
        pixels_per_km = 55
        start_x = 100
        car_x = start_x + (distance_km * pixels_per_km) - 80 
        
        time_per_5km = duration / 4
        current_block_time = time_elapsed % time_per_5km
        fake_minutes = int((current_block_time / time_per_5km) * 60)
        time_str = f"00:{fake_minutes:02d}:00" 
        
        wheel_angle = (i / fps) * 360 * 2  
        
        frame_file = f"temp_frames/sci_frame_{i:04d}.png"
        draw_scene_frame(car_x, wheel_angle, time_str, distance_km, frame_file)

    print("Rendering Science MP4...")
    cmd = [
        FFMPEG_PATH, "-y", "-framerate", str(fps), "-i", "temp_frames/sci_frame_%04d.png",
        "-i", audio_file, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", "science_lesson.mp4"
    ]
    
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    print("\nSUCCESS! Video generated: science_lesson.mp4")

if __name__ == "__main__":
    main()