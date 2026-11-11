import shutil
from app import fonts
import os
import sys
import subprocess
import asyncio
from app import tts_compat as edge_tts
from PIL import Image, ImageDraw, ImageFont
from mutagen.mp3 import MP3

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

def draw_dot(draw, x, y, color=(80, 255, 80), size=5):
    draw.ellipse([x-size, y-size, x+size, y+size], fill=color)

def draw_scene(img, scene_idx):
    draw = ImageDraw.Draw(img)
    font_b = fonts.truetype("arialbd.ttf", 35)
    font_r = fonts.truetype("arial.ttf", 28)
    font_small = fonts.truetype("arial.ttf", 22)
    
    # Title
    draw.text((WIDTH // 2, 40), "Covalent Bonds and Compounds", font=font_b, fill=HIGHLIGHT_COLOR, anchor="ma")

    if scene_idx == 0:
        # Introduction Text
        lines = [
            "A covalent bond is formed by the sharing",
            "of electrons between two atoms.",
            "Let's look at examples of single, double, and triple bonds."
        ]
        y = 250
        for line in lines:
            draw.text((WIDTH // 2, y), line, font=font_r, fill=TEXT_COLOR, anchor="ma")
            y += 60

    elif scene_idx == 1:
        # Hydrogen (H2) - Single Bond
        draw.text((WIDTH // 2, 100), "1. Single Covalent Bond (H₂)", font=font_b, fill=TEXT_COLOR, anchor="ma")
        
        cx1, cy1 = 480, 350
        cx2, cy2 = 800, 350
        
        # Overlapping circles
        draw.ellipse([cx1-110, cy1-110, cx1+110, cy1+110], outline=TEXT_COLOR, width=2)
        draw.ellipse([cx2-110, cy2-110, cx2+110, cy2+110], outline=TEXT_COLOR, width=2)
        
        # Nucleus
        draw.text((cx1, cy1), "H", font=font_b, fill=(255, 100, 100), anchor="mm")
        draw.text((cx2, cy2), "H", font=font_b, fill=(255, 100, 100), anchor="mm")
        
        # Shared electrons in the overlap
        draw_dot(draw, cx1 + 80, cy1 - 20, (80, 255, 80), 6)
        draw_dot(draw, cx2 - 80, cy2 + 20, (80, 255, 80), 6)
        
        draw.text((WIDTH // 2, 520), "• Two atoms share 1 electron each.", font=font_r, fill=TEXT_COLOR, anchor="ma")
        draw.text((WIDTH // 2, 570), "• Results in a Single Bond (H - H).", font=font_r, fill=HIGHLIGHT_COLOR, anchor="ma")

    elif scene_idx == 2:
        # Oxygen (O2) - Double Bond
        draw.text((WIDTH // 2, 100), "2. Double Covalent Bond (O₂)", font=font_b, fill=TEXT_COLOR, anchor="ma")
        
        cx1, cy1 = 480, 350
        cx2, cy2 = 800, 350
        
        draw.ellipse([cx1-120, cy1-120, cx1+120, cy1+120], outline=TEXT_COLOR, width=2)
        draw.ellipse([cx2-120, cy2-120, cx2+120, cy2+120], outline=TEXT_COLOR, width=2)
        
        draw.text((cx1, cy1), "O", font=font_b, fill=(255, 100, 100), anchor="mm")
        draw.text((cx2, cy2), "O", font=font_b, fill=(255, 100, 100), anchor="mm")
        
        # Shared electrons (2 pairs = 4 dots)
        draw_dot(draw, cx1 + 85, cy1 - 25, (80, 255, 80), 6)
        draw_dot(draw, cx2 - 85, cy2 + 25, (80, 255, 80), 6)
        draw_dot(draw, cx1 + 85, cy1 + 25, (80, 255, 80), 6)
        draw_dot(draw, cx2 - 85, cy2 - 25, (80, 255, 80), 6)
        
        draw.text((WIDTH // 2, 520), "• Two atoms share 2 electrons each.", font=font_r, fill=TEXT_COLOR, anchor="ma")
        draw.text((WIDTH // 2, 570), "• Results in a Double Bond (O = O).", font=font_r, fill=HIGHLIGHT_COLOR, anchor="ma")

    elif scene_idx == 3:
        # Nitrogen (N2) - Triple Bond
        draw.text((WIDTH // 2, 100), "3. Triple Covalent Bond (N₂)", font=font_b, fill=TEXT_COLOR, anchor="ma")
        
        cx1, cy1 = 480, 350
        cx2, cy2 = 800, 350
        
        draw.ellipse([cx1-130, cy1-130, cx1+130, cy1+130], outline=TEXT_COLOR, width=2)
        draw.ellipse([cx2-130, cy2-130, cx2+130, cy2+130], outline=TEXT_COLOR, width=2)
        
        draw.text((cx1, cy1), "N", font=font_b, fill=(255, 100, 100), anchor="mm")
        draw.text((cx2, cy2), "N", font=font_b, fill=(255, 100, 100), anchor="mm")
        
        # Shared electrons (3 pairs = 6 dots)
        draw_dot(draw, cx1 + 95, cy1 - 40, (80, 255, 80), 6)
        draw_dot(draw, cx2 - 95, cy2 + 40, (80, 255, 80), 6)
        draw_dot(draw, cx1 + 95, cy1, (80, 255, 80), 6)
        draw_dot(draw, cx2 - 95, cy2, (80, 255, 80), 6)
        draw_dot(draw, cx1 + 95, cy1 + 40, (80, 255, 80), 6)
        draw_dot(draw, cx2 - 95, cy2 - 40, (80, 255, 80), 6)
        
        draw.text((WIDTH // 2, 520), "• Two atoms share 3 electrons each.", font=font_r, fill=TEXT_COLOR, anchor="ma")
        draw.text((WIDTH // 2, 570), "• Results in a Triple Bond (N ≡ N).", font=font_r, fill=HIGHLIGHT_COLOR, anchor="ma")

def main():
    scenes = [
        ("A covalent bond is formed by the sharing of electrons between two atoms. Let's look at examples of single, double, and triple bonds.", 0),
        ("First, the formation of Hydrogen. Two hydrogen atoms share one electron each to form a single covalent bond.", 1),
        ("Next, Oxygen. Two oxygen atoms share two electrons each to complete their octet, forming a double bond.", 2),
        ("Finally, Nitrogen. Two nitrogen atoms share three electrons each to achieve a stable configuration, forming a triple bond.", 3)
    ]
    
    parts = []
    for i, (text, sc) in enumerate(scenes):
        af = f"temp_frames/chem_audio_{i}.mp3"
        dur = asyncio.run(generate_audio(text, af))
        for f in range(int(dur * 24)):
            img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
            draw_scene(img, sc)
            img.save(f"temp_frames/chem_{i}_{f:04d}.png")
        
        clip = f"temp_frames/chem_clip_{i}.mp4"
        cmd = [FFMPEG_PATH, "-y", "-framerate", "24", "-i", f"temp_frames/chem_{i}_%04d.png", "-i", af, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", clip]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        parts.append(clip)

    with open("temp_frames/chem_concat.txt", "w") as f:
        for p in parts: f.write(f"file '{os.path.abspath(p)}'\n")
    subprocess.run([FFMPEG_PATH, "-y", "-f", "concat", "-safe", "0", "-i", "temp_frames/chem_concat.txt", "-c", "copy", "covalent_bonds.mp4"], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    print("SUCCESS! Video generated: covalent_bonds.mp4")

if __name__ == "__main__":
    main()