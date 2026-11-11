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
BG_COLOR = (30, 40, 50) 
TEXT_COLOR = (255, 255, 255)
HIGHLIGHT_COLOR = (255, 200, 0)
FFMPEG_PATH = shutil.which("ffmpeg") or "ffmpeg"
os.makedirs("temp_frames", exist_ok=True)

async def generate_audio(text, filename):
    communicate = edge_tts.Communicate(text, "en-US-ChristopherNeural")
    await communicate.save(filename)
    return MP3(filename).info.length

def draw_scene(img, scene_idx):
    draw = ImageDraw.Draw(img)
    font_b = fonts.truetype("arialbd.ttf", 30)
    font_r = fonts.truetype("arial.ttf", 24)
    font_small = fonts.truetype("arial.ttf", 20)
    
    draw.text((WIDTH // 2, 30), "Trigonometry: Balloon Problem", font=font_b, fill=HIGHLIGHT_COLOR, anchor="ma")

    # --- DRAW THE GEOMETRY (Always visible) ---
    ground_y = 550
    eye_level = 520 # Girl's height is 1.2m, so eyes are slightly above ground
    girl_x = 150
    
    # Draw Ground
    draw.line([50, ground_y, WIDTH-50, ground_y], fill=TEXT_COLOR, width=2)
    
    # Draw Girl (Simplified stick figure)
    draw.line([girl_x, ground_y, girl_x, eye_level - 40], fill=(200, 200, 200), width=4)
    draw.ellipse([girl_x-15, eye_level-60, girl_x+15, eye_level-30], outline=(200, 200, 200), width=3)
    draw.text((girl_x - 30, ground_y + 10), "Girl (1.2m)", font=font_small, fill=(200, 200, 200))

    # Draw Horizontal line from Girl's eyes
    draw.line([girl_x, eye_level, 900, eye_level], fill=(150, 150, 150), width=1)

    # Base of the triangles (Point D and Point C)
    point_d_x = 450
    point_c_x = 800
    
    # Height of the balloon (87m above eye level)
    # We scale it down to fit the screen. 87m -> 300px.
    balloon_y = eye_level - 300

    # Draw the vertical line representing the balloon's path
    draw.line([point_d_x, eye_level, point_d_x, balloon_y], fill=(150, 150, 150), width=2) # Line CD
    draw.line([point_c_x, eye_level, point_c_x, balloon_y], fill=(150, 150, 150), width=2) # Line CE

    # Draw Balloon A (Initial position, 60 deg)
    draw.ellipse([point_d_x-15, balloon_y-20, point_d_x+15, balloon_y+10], fill=(255, 80, 80))
    draw.text((point_d_x-20, balloon_y-45), "A", font=font_b, fill=(255, 80, 80))
    
    # Draw Balloon B (Final position, 30 deg)
    draw.ellipse([point_c_x-15, balloon_y-20, point_c_x+15, balloon_y+10], fill=(80, 255, 80))
    draw.text((point_c_x-20, balloon_y-45), "B", font=font_b, fill=(80, 255, 80))

    # Draw Triangles (The rays from the girl's eyes)
    draw.line([girl_x, eye_level, point_d_x, balloon_y], fill=(255, 200, 0), width=3) # Ray to A
    draw.line([girl_x, eye_level, point_c_x, balloon_y], fill=(255, 200, 0), width=3) # Ray to B

    # Draw Right Angle symbols at D and C
    draw.line([point_d_x, eye_level, point_d_x-15, eye_level], fill=TEXT_COLOR, width=2)
    draw.line([point_c_x, eye_level, point_c_x-15, eye_level], fill=TEXT_COLOR, width=2)

    # Labels for the diagram
    draw.text((point_d_x - 25, eye_level + 10), "D", font=font_b, fill=TEXT_COLOR)
    draw.text((point_c_x - 25, eye_level + 10), "C", font=font_b, fill=TEXT_COLOR)
    draw.text((point_d_x - 40, balloon_y + 40), "87m", font=font_small, fill=(150, 150, 150))
    draw.text((point_d_x + 20, eye_level - 80), "60°", font=font_small, fill=(255, 200, 0))
    draw.text((point_c_x - 60, eye_level - 40), "30°", font=font_small, fill=(255, 200, 0))

    # --- SCENE TEXT LOGIC ---
    text_x = 700 # Right side of the screen
    y = 100
    
    if scene_idx == 0:
        draw.text((text_x, y), "Given:", font=font_b, fill=HIGHLIGHT_COLOR)
        draw.text((text_x, y+40), "Girl's height = 1.2 m", font=font_r, fill=TEXT_COLOR)
        draw.text((text_x, y+80), "Balloon height = 88.2 m", font=font_r, fill=TEXT_COLOR)
        draw.text((text_x, y+120), "Height above girl's eyes:", font=font_r, fill=TEXT_COLOR)
        draw.text((text_x, y+160), "88.2 - 1.2 = 87 m", font=font_b, fill=(80, 255, 80))

    elif scene_idx == 1:
        draw.text((text_x, y), "Step 1: In ΔBEC", font=font_b, fill=HIGHLIGHT_COLOR)
        draw.text((text_x, y+50), "tan 30° = BE / CE", font=font_r, fill=TEXT_COLOR)
        draw.text((text_x, y+100), "1 / √3 = 87 / CE", font=font_r, fill=TEXT_COLOR)
        draw.text((text_x, y+150), "CE = 87√3", font=font_b, fill=(80, 255, 80))

    elif scene_idx == 2:
        draw.text((text_x, y), "Step 2: In ΔADC", font=font_b, fill=HIGHLIGHT_COLOR)
        draw.text((text_x, y+50), "tan 60° = AD / CD", font=font_r, fill=TEXT_COLOR)
        draw.text((text_x, y+100), "√3 = 87 / CD", font=font_r, fill=TEXT_COLOR)
        draw.text((text_x, y+150), "CD = 87 / √3 = 29√3", font=font_b, fill=(80, 255, 80))

    elif scene_idx == 3:
        draw.text((text_x, y), "Step 3: Distance (DE)", font=font_b, fill=HIGHLIGHT_COLOR)
        draw.text((text_x, y+50), "DE = CE - CD", font=font_r, fill=TEXT_COLOR)
        draw.text((text_x, y+100), "DE = 87√3 - 29√3", font=font_r, fill=TEXT_COLOR)
        draw.text((text_x, y+150), "DE = 58√3 m", font=font_b, fill=(80, 255, 80))
        
        # Highlight the distance on the diagram
        draw.line([point_d_x, eye_level + 20, point_c_x, eye_level + 20], fill=(80, 255, 80), width=4)
        draw.text((point_d_x + 100, eye_level + 30), "Distance travelled", font=font_small, fill=(80, 255, 80))

def main():
    scenes = [
        ("Let us solve the balloon problem. The girl's height is 1.2 meters and the balloon is at 88.2 meters. The height of the balloon above the girl's eyes is 88.2 minus 1.2, which equals 87 meters.", 0),
        ("Step 1. In right triangle B E C, tan 30 degrees equals B E over C E. Substituting the values, one over root 3 equals 87 over C E. Therefore, C E equals 87 root 3.", 1),
        ("Step 2. In right triangle A D C, tan 60 degrees equals A D over C D. Substituting the values, root 3 equals 87 over C D. Therefore, C D equals 87 over root 3, which is 29 root 3.", 2),
        ("Step 3. The distance travelled by the balloon, D E, is C E minus C D. This is 87 root 3 minus 29 root 3, which equals 58 root 3 meters.", 3)
    ]
    
    parts = []
    for i, (text, sc) in enumerate(scenes):
        af = f"temp_frames/trig_audio_{i}.mp3"
        dur = asyncio.run(generate_audio(text, af))
        for f in range(int(dur * 24)):
            img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
            draw_scene(img, sc)
            img.save(f"temp_frames/trig_{i}_{f:04d}.png")
        
        clip = f"temp_frames/trig_clip_{i}.mp4"
        cmd = [FFMPEG_PATH, "-y", "-framerate", "24", "-i", f"temp_frames/trig_{i}_%04d.png", "-i", af, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", clip]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        parts.append(clip)

    with open("temp_frames/trig_concat.txt", "w") as f:
        for p in parts: f.write(f"file '{os.path.abspath(p)}'\n")
    subprocess.run([FFMPEG_PATH, "-y", "-f", "concat", "-safe", "0", "-i", "temp_frames/trig_concat.txt", "-c", "copy", "trig_balloon.mp4"], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    print("SUCCESS! Video generated: trig_balloon.mp4")

if __name__ == "__main__":
    main()