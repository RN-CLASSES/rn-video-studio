import os
import sys
import subprocess
import asyncio
import edge_tts
from PIL import Image, ImageDraw, ImageFont
from mutagen.mp3 import MP3

WIDTH, HEIGHT = 1280, 720
BG_COLOR = (30, 40, 50)      
TEXT_COLOR = (255, 255, 255) 
HIGHLIGHT_COLOR = (255, 200, 0) 
VOICE = "en-US-ChristopherNeural" 
FFMPEG_PATH = r"C:\Users\jitan\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin\ffmpeg.exe"

os.makedirs("temp_frames", exist_ok=True)

def draw_frame(text_lines, filename):
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)
    y_offset = 60
    for line in text_lines:
        if line.startswith("Given") or line.startswith("Formula") or line.startswith("Substituting"):
            font = ImageFont.truetype("arialbd.ttf", 40) 
            color = HIGHLIGHT_COLOR
        elif "⇒" in line:
            font = ImageFont.truetype("seguisym.ttf", 40) 
            color = TEXT_COLOR
        else:
            font = ImageFont.truetype("arial.ttf", 40)
            color = TEXT_COLOR
        bbox = draw.textbbox((0, 0), line, font=font)
        x = (WIDTH - (bbox[2] - bbox[0])) // 2
        draw.text((x, y_offset), line, font=font, fill=color)
        y_offset += 60
    img.save(filename)

async def generate_audio(text, filename):
    communicate = edge_tts.Communicate(text, VOICE)
    await communicate.save(filename)
    audio = MP3(filename)
    return audio.info.length

def run_ffmpeg(cmd):
    return subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True).returncode == 0

def main():
    if len(sys.argv) < 4:
        print("Usage: python word_problem.py <topic> <distance> <time>")
        return
        
    dist = sys.argv[2]
    time = sys.argv[3]
    
    try:
        speed = float(dist) / float(time)
        # Format speed cleanly (e.g., 60.0 -> 60)
        speed_str = str(int(speed)) if speed.is_integer() else f"{speed:.2f}"
    except:
        print("Invalid numbers.")
        return

    scenes = []
    
    # 1. Given
    scenes.append((
        ["Given:", f"Distance covered = {dist} km", f"Time taken = {time} hours"],
        f"Given. Distance covered is {dist} kilometers. Time taken is {time} hours."
    ))
    
    # 2. Formula
    scenes.append((
        ["Formula:", "Speed = Distance / Time"],
        "We know that Speed equals Distance divided by Time."
    ))
    
    # 3. Substitution
    scenes.append((
        ["Substituting the values:", f"⇒ Speed = {dist} / {time}"],
        f"Substituting the values, we get Speed equals {dist} divided by {time}."
    ))
    
    # 4. Answer
    scenes.append((
        [f"⇒ Speed = {speed_str} km/h", f"Therefore, the speed is {speed_str} km/h"],
        f"Therefore, the speed is {speed_str} kilometers per hour."
    ))

    print("Generating Audio and Frames...")
    video_parts = []
    current_board = []
    
    for i, (new_lines, voice_text) in enumerate(scenes):
        print(f"   Processing Scene {i+1}...")
        current_board = list(new_lines) 
        
        audio_file = f"temp_frames/scene_{i}.mp3"
        duration = asyncio.run(generate_audio(voice_text, audio_file))
        
        img_file = f"temp_frames/scene_{i}.png"
        draw_frame(current_board, img_file)
        
        clip_file = f"temp_frames/clip_{i}.mp4"
        cmd = [FFMPEG_PATH, "-y", "-loop", "1", "-framerate", "24", "-i", img_file, "-i", audio_file,
               "-c:v", "libx264", "-tune", "stillimage", "-c:a", "aac", "-b:a", "192k",
               "-pix_fmt", "yuv420p", "-t", str(duration), "-shortest", clip_file]
        if run_ffmpeg(cmd): video_parts.append(clip_file)

    with open("temp_frames/concat.txt", "w") as f:
        for part in video_parts: f.write(f"file '{os.path.abspath(part)}'\n")

    final_cmd = [FFMPEG_PATH, "-y", "-f", "concat", "-safe", "0", "-i", "temp_frames/concat.txt", "-c", "copy", "word_problem.mp4"]
    if run_ffmpeg(final_cmd): print("\nSUCCESS! Video generated: word_problem.mp4")

if __name__ == "__main__":
    main()