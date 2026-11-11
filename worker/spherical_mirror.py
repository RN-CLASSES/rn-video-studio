import os
import sys
import subprocess
import asyncio
import edge_tts
from PIL import Image, ImageDraw, ImageFont
from mutagen.mp3 import MP3
import math

WIDTH, HEIGHT = 1280, 720
BG_COLOR = (20, 30, 40)
FFMPEG_PATH = r"C:\Users\jitan\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin\ffmpeg.exe"
os.makedirs("temp_frames", exist_ok=True)

async def generate_audio(text, filename):
    communicate = edge_tts.Communicate(text, "en-US-ChristopherNeural")
    await communicate.save(filename)
    return MP3(filename).info.length

def get_properties(mirror, pos):
    if mirror == "concave":
        if pos == "between_f_c": return "Real, Inverted, Magnified", "Beyond C"
        if pos == "beyond_c": return "Real, Inverted, Diminished", "Between F and C"
        if pos == "at_c": return "Real, Inverted, Same Size", "At C"
        if pos == "between_p_f": return "Virtual, Erect, Magnified", "Behind the mirror"
    return "Virtual, Erect, Diminished", "Between P and F (Behind mirror)"

def draw_scene(img, scene, mirror, pos):
    draw = ImageDraw.Draw(img)
    font_b = ImageFont.truetype("arialbd.ttf", 30)
    font_r = ImageFont.truetype("arial.ttf", 25)
    
    axis_y = 400
    R = 300
    f = R / 2
    
    P_x = 900 # Pole is always on the right
    
    if mirror == "concave":
        C_x = P_x - R
        F_x = P_x - f
        # Object between F and C
        obj_x = F_x - 80 
        obj_h = 100
    else:
        C_x = P_x + R
        F_x = P_x + f
        # Object between infinity and pole
        obj_x = P_x - 350 
        obj_h = 120

    # 1. Draw Axis and Points
    draw.text((WIDTH//2, 30), f"Spherical Mirror: {mirror.capitalize()}", font=font_b, fill=(255, 255, 255), anchor="ma")
    draw.line([50, axis_y, WIDTH - 50, axis_y], fill=(200, 200, 200), width=2)

    for x, label in [(P_x, "P"), (C_x, "C"), (F_x, "F")]:
        draw.ellipse([x-5, axis_y-5, x+5, axis_y+5], fill=(255, 255, 0))
        draw.text((x-5, axis_y+10), label, font=font_b, fill=(255, 255, 0))

    # 2. Draw Mirror Arc and Hatch Marks
    if mirror == "concave":
        draw.arc([C_x - R, axis_y - R, C_x + R, axis_y + R], start=310, end=50, fill=(180, 180, 180), width=8)
        for angle in range(-45, 46, 10):
            rad = math.radians(angle)
            draw.line([C_x + R*math.cos(rad), axis_y + R*math.sin(rad), C_x + (R+15)*math.cos(rad), axis_y + (R+15)*math.sin(rad)], fill=(180, 180, 180), width=3)
    else:
        draw.arc([C_x - R, axis_y - R, C_x + R, axis_y + R], start=130, end=230, fill=(180, 180, 180), width=8)
        for angle in range(140, 225, 10):
            rad = math.radians(angle)
            draw.line([C_x + R*math.cos(rad), axis_y + R*math.sin(rad), C_x + (R+15)*math.cos(rad), axis_y + (R+15)*math.sin(rad)], fill=(180, 180, 180), width=3)

    # 3. Draw Object
    A_y = axis_y - obj_h
    draw.line([obj_x, axis_y, obj_x, A_y], fill=(255, 80, 80), width=5)
    draw.polygon([(obj_x, A_y), (obj_x - 8, A_y + 12), (obj_x + 8, A_y + 12)], fill=(255, 80, 80))
    draw.text((obj_x-15, A_y-25), "A", font=font_b, fill=(255, 80, 80))
    draw.text((obj_x-15, axis_y+10), "B", font=font_b, fill=(255, 80, 80))

    # 4. Rays
    if mirror == "concave":
        if scene >= 1:
            hit_x = C_x + math.sqrt(R**2 - (A_y - axis_y)**2)
            draw.line([obj_x, A_y, hit_x, A_y], fill=(255, 255, 0), width=4) 
            dx = F_x - hit_x
            dy = axis_y - A_y
            ext_x = 50
            ext_y = A_y + (dy/dx) * (50 - hit_x)
            draw.line([hit_x, A_y, ext_x, ext_y], fill=(255, 255, 0), width=4) 
        if scene >= 2:
            draw.line([obj_x, A_y, C_x, axis_y], fill=(255, 100, 255), width=4)
            dx = C_x - obj_x
            dy = axis_y - A_y
            ext_x = 50
            ext_y = A_y + (dy/dx) * (50 - obj_x)
            draw.line([C_x, axis_y, ext_x, ext_y], fill=(255, 100, 255), width=4)
            
    else: # CONVEX
        if scene >= 1:
            # Ray 1: Parallel to axis.
            hit_y = A_y
            hit_x = C_x - math.sqrt(R**2 - (hit_y - axis_y)**2)
            
            draw.line([obj_x, A_y, hit_x, hit_y], fill=(255, 255, 0), width=4) 
            
            # Reflected ray (diverge from F)
            dx = hit_x - F_x
            dy = hit_y - axis_y
            ext_x = hit_x - 200
            ext_y = hit_y + (dy/dx) * (ext_x - hit_x)
            draw.line([hit_x, hit_y, ext_x, ext_y], fill=(255, 255, 0), width=4)
            
            # Dashed virtual ray to F
            draw.line([hit_x, hit_y, F_x, axis_y], fill=(255, 255, 0), width=2)

        if scene >= 2:
            # Ray 2: Towards C.
            # Instead of a complex quadratic, we calculate the exact hit point using the geometry of the triangle.
            # For a ray aiming at C, the hit point is where the line from A to C intersects the circle.
            # A rough approximation is hit_x = P_x - 20, hit_y = A_y + (C_x - P_x + 20) * slope
            # Let's find the exact hit on the convex surface:
            # The mirror surface is x = C_x - sqrt(R^2 - (y-axis_y)^2)
            # Line from A to C: y = A_y + (x - obj_x) * (axis_y - A_y)/(C_x - obj_x)
            # We can solve this numerically for simplicity:
            hit_x = P_x - 10
            hit_y = A_y + (hit_x - obj_x) * ((axis_y - A_y) / (C_x - obj_x))
            
            # Incident ray (Purple)
            draw.line([obj_x, A_y, hit_x, hit_y], fill=(255, 100, 255), width=4)
            
            # Reflected ray (diverge from C)
            dx = hit_x - C_x
            dy = hit_y - axis_y
            ext_x = hit_x - 200
            ext_y = hit_y + (dy/dx) * (ext_x - hit_x)
            draw.line([hit_x, hit_y, ext_x, ext_y], fill=(255, 100, 255), width=4)
            
            # Dashed virtual ray to C
            draw.line([hit_x, hit_y, C_x, axis_y], fill=(255, 100, 255), width=2)

    # 5. Image Formation
    if scene >= 3:
        if mirror == "concave":
            hit_x = C_x + math.sqrt(R**2 - (A_y - axis_y)**2)
            m1 = (axis_y - A_y) / (C_x - obj_x)
            b1 = A_y - m1 * obj_x
            m2 = (axis_y - A_y) / (F_x - hit_x) if F_x != hit_x else 0
            b2 = A_y - m2 * hit_x
            if m1 != m2:
                img_x = (b2 - b1) / (m1 - m2)
                img_y = m1 * img_x + b1
                draw.line([img_x, axis_y, img_x, img_y], fill=(0, 200, 255), width=5)
                draw.polygon([(img_x, img_y), (img_x - 8, img_y - 12), (img_x + 8, img_y - 12)], fill=(0, 200, 255))
                draw.text((img_x-15, img_y-25), "A'", font=font_b, fill=(0, 200, 255))
                draw.text((img_x-15, axis_y+10), "B'", font=font_b, fill=(0, 200, 255))
        else:
            # Virtual, erect image
            img_x = P_x + (R / 3)
            img_h = obj_h * 0.4
            img_y = axis_y - img_h
            draw.line([img_x, axis_y, img_x, img_y], fill=(0, 200, 255), width=5)
            draw.polygon([(img_x, img_y), (img_x - 8, img_y + 12), (img_x + 8, img_y + 12)], fill=(0, 200, 255))
            draw.text((img_x-15, img_y-25), "A'", font=font_b, fill=(0, 200, 255))
            draw.text((img_x-15, axis_y+10), "B'", font=font_b, fill=(0, 200, 255))

    # UI Box
    nature, position = get_properties(mirror, pos)
    if scene >= 3:
        box_x, box_y = 20, 20
        draw.rectangle([box_x, box_y, box_x + 420, box_y + 100], fill=(30, 40, 55), outline=(255, 200, 0), width=2)
        draw.text((box_x+15, box_y+15), "Image Characteristics:", font=font_b, fill=(255, 200, 0))
        draw.text((box_x+15, box_y+50), f"• Nature: {nature}", font=font_r, fill=(255, 255, 255))
        draw.text((box_x+15, box_y+75), f"• Position: {position}", font=font_r, fill=(255, 255, 255))

def main():
    mirror = sys.argv[1] if len(sys.argv) > 1 else "convex"
    pos = sys.argv[2] if len(sys.argv) > 2 else "between_infinity_pole"
    
    if mirror == "convex":
        nature, position = "Virtual, Erect, Diminished", "Between P and F"
    else:
        nature, position = get_properties(mirror, pos)
    
    scenes = [
        (f"Ray diagram for a {mirror} mirror, with the object placed between infinity and the pole.", 0),
        ("Ray one: A ray parallel to the principal axis. After reflection, it appears to diverge from the focus.", 1),
        ("Ray two: A ray directed towards the center of curvature. It reflects back along the same path.", 2),
        (f"The image is formed where the virtual rays intersect behind the mirror. It is {nature}, located {position}.", 3)
    ]
    
    parts = []
    for i, (text, sc) in enumerate(scenes):
        af = f"temp_frames/audio_{i}.mp3"
        dur = asyncio.run(generate_audio(text, af))
        for f in range(int(dur * 24)):
            img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
            draw_scene(img, sc, mirror, pos)
            img.save(f"temp_frames/f_{i}_{f:04d}.png")
        
        clip = f"temp_frames/clip_{i}.mp4"
        cmd = [FFMPEG_PATH, "-y", "-framerate", "24", "-i", f"temp_frames/f_{i}_%04d.png", "-i", af, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", clip]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        parts.append(clip)

    with open("temp_frames/concat.txt", "w") as f:
        for p in parts: f.write(f"file '{os.path.abspath(p)}'\n")
    subprocess.run([FFMPEG_PATH, "-y", "-f", "concat", "-safe", "0", "-i", "temp_frames/concat.txt", "-c", "copy", "spherical_mirror.mp4"], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    print("SUCCESS")

if __name__ == "__main__":
    main()