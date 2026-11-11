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
DEF_BG_COLOR = (30, 40, 55)
FFMPEG_PATH = shutil.which("ffmpeg") or "ffmpeg"

os.makedirs("temp_frames", exist_ok=True)

async def generate_audio(text, filename):
    communicate = edge_tts.Communicate(text, "en-US-ChristopherNeural")
    await communicate.save(filename)
    return MP3(filename).info.length

def draw_scene_frame(ray_progress, filename):
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)
    
    font_bold = fonts.truetype("arialbd.ttf", 35)
    font_regular = fonts.truetype("arial.ttf", 30)
    font_small = fonts.truetype("arialbd.ttf", 30) # Slightly larger for i and r
    
    # 1. Draw the Mirror
    mirror_y = 450
    draw.rectangle([150, mirror_y, WIDTH - 150, mirror_y + 20], fill=(150, 150, 200))
    draw.text((WIDTH - 280, mirror_y + 30), "Plane Mirror", font=font_regular, fill=(255, 255, 255))
    
    # 2. Draw the Normal Line
    normal_x = WIDTH // 2
    draw.line([normal_x, mirror_y, normal_x, mirror_y - 250], fill=(255, 255, 255), width=2)
    draw.text((normal_x + 10, mirror_y - 260), "Normal", font=font_regular, fill=(255, 255, 255))
    
    # 3. Draw the Incident Ray (Top Left to Center)
    incident_start = (normal_x - 200, mirror_y - 200)
    incident_end = (normal_x, mirror_y)
    
    if ray_progress > 0:
        curr_x = incident_start[0] + (incident_end[0] - incident_start[0]) * min(ray_progress, 1.0)
        curr_y = incident_start[1] + (incident_end[1] - incident_start[1]) * min(ray_progress, 1.0)
        draw.line([incident_start, (curr_x, curr_y)], fill=(255, 80, 80), width=4)
        draw.text((normal_x - 230, mirror_y - 180), "Incident Ray", font=font_regular, fill=(255, 80, 80))
        
    # 4. Draw the Reflected Ray (Center to Top Right)
    reflected_end = (normal_x + 200, mirror_y - 200)
    
    if ray_progress >= 1.0:
        reflect_progress = min(ray_progress - 1.0, 1.0)
        curr_x = incident_end[0] + (reflected_end[0] - incident_end[0]) * reflect_progress
        curr_y = incident_end[1] + (reflected_end[1] - incident_end[1]) * reflect_progress
        draw.line([incident_end, (curr_x, curr_y)], fill=(80, 255, 80), width=4)
        draw.text((normal_x + 80, mirror_y - 180), "Reflected Ray", font=font_regular, fill=(80, 255, 80))

        # 5. Draw the Arcs and Angles (Only when both rays are fully drawn)
        if ray_progress >= 2.0:
            arc_radius = 80
            
            # Incident Angle Arc (225 to 270 degrees)
            draw.arc([normal_x - arc_radius, mirror_y - arc_radius, normal_x + arc_radius, mirror_y + arc_radius], 
                     start=225, end=270, fill=(255, 255, 0), width=3)
            
            # Reflected Angle Arc (270 to 315 degrees)
            draw.arc([normal_x - arc_radius, mirror_y - arc_radius, normal_x + arc_radius, mirror_y + arc_radius], 
                     start=270, end=315, fill=(255, 255, 0), width=3)
            
            # --- MATHEMATICAL PLACEMENT OF i and r ---
            # Instead of guessing the coordinates, we calculate the midpoint of the arc.
            # Midpoint of 225 and 270 is 247.5 degrees
            # Midpoint of 270 and 315 is 292.5 degrees
            text_radius = arc_radius - 25 
            
            i_angle_rad = math.radians(247.5)
            i_x = normal_x + text_radius * math.cos(i_angle_rad)
            i_y = mirror_y + text_radius * math.sin(i_angle_rad)
            draw.text((i_x, i_y), "i", font=font_small, fill=(255, 255, 0), anchor="mm")
            
            r_angle_rad = math.radians(292.5)
            r_x = normal_x + text_radius * math.cos(r_angle_rad)
            r_y = mirror_y + text_radius * math.sin(r_angle_rad)
            draw.text((r_x, r_y), "r", font=font_small, fill=(255, 255, 0), anchor="mm")

    # 6. UI Text
    y_offset = 60
    text_lines = [
        "Laws of Reflection",
        "1. Angle of Incidence (i) = Angle of Reflection (r)",
        "2. Incident ray, Normal, and Reflected ray lie on the same plane."
    ]
    for i, line in enumerate(text_lines):
        f = font_bold if i == 0 else font_regular
        color = (255, 255, 255) if i == 0 else (255, 200, 0)
        draw.text((WIDTH // 2, y_offset), line, font=f, fill=color, anchor="ma")
        y_offset += 50

    # 7. Definition Panel
    draw.rectangle([0, 600, WIDTH, HEIGHT], fill=DEF_BG_COLOR)
    draw.text((40, 615), "Definitions:", font=font_bold, fill=(255, 255, 255))
    draw.text((40, 650), "• Angle of Incidence: The angle between the incident ray and the normal.", font=font_regular, fill=(200, 200, 200))
    draw.text((40, 680), "• Angle of Reflection: The angle between the reflected ray and the normal.", font=font_regular, fill=(200, 200, 200))

    img.save(filename)

def main():
    # Updated voiceover to include the 2nd law
    voice_text = "When light falls on a plane mirror, it bounces back. This is called reflection. There are two laws of reflection. First, the angle of incidence is always equal to the angle of reflection. Second, the incident ray, the normal, and the reflected ray all lie on the same plane."
    audio_file = "temp_frames/reflection_audio.mp3"
    duration = asyncio.run(generate_audio(voice_text, audio_file))
    
    print(f"Generating {duration:.2f} seconds of animation...")
    fps = 24
    total_frames = int(duration * fps)
    
    for i in range(total_frames):
        time_elapsed = i / fps
        progress = time_elapsed / duration
        
        if progress < 0.33:
            ray_progress = (progress / 0.33) * 1.0
        elif progress < 0.66:
            ray_progress = 1.0 + ((progress - 0.33) / 0.33)
        else:
            ray_progress = 2.0 + ((progress - 0.66) / 0.34)
            
        frame_file = f"temp_frames/ref_{i:04d}.png"
        draw_scene_frame(ray_progress, frame_file)

    print("Rendering Reflection MP4...")
    cmd = [
        FFMPEG_PATH, "-y", "-framerate", str(fps), "-i", "temp_frames/ref_%04d.png",
        "-i", audio_file, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", "reflection_lesson.mp4"
    ]
    
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    print("\nSUCCESS! Video generated: reflection_lesson.mp4")

if __name__ == "__main__":
    main()