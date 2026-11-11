import os
import sys
import subprocess
import asyncio
import edge_tts
from PIL import Image, ImageDraw, ImageFont
import sympy as sp
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
        if line.startswith("Step") or line.startswith("Roots") or line.startswith("Given") or line.startswith("Method") or line.startswith("Either"):
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

def format_screen(text):
    text = text.replace("**2", "²").replace("**3", "³").replace("*", "")
    text = text.replace("-", " - ").replace("+", " + ").replace("=", " = ")
    return " ".join(text.split())

def format_voice(text):
    text = text.replace("**2", " squared").replace("**3", " cubed").replace("*", "")
    text = text.replace("-", " minus ").replace("+", " plus ").replace("=", " equals ")
    return " ".join(text.split())

def main():
    eq_string = sys.argv[1] if len(sys.argv) > 1 else "x**2 - 5*x + 6 = 0"
    x, y = sp.symbols('x y')
    scenes = []
    
    # Check for Simultaneous Equations
    if ";" in eq_string or "," in eq_string:
        parts = eq_string.replace(",", ";").split(";")
        if len(parts) == 2:
            eq1_str, eq2_str = parts[0].strip(), parts[1].strip()
            eq1 = sp.sympify(eq1_str.replace("=", "-(") + ")")
            eq2 = sp.sympify(eq2_str.replace("=", "-(") + ")")
            sol = sp.solve((eq1, eq2), (x, y))
            scenes.append((["Simultaneous Equations:", format_screen(eq1_str), format_screen(eq2_str)], "Let us solve these simultaneous equations."))
            scenes.append((["Method: Substitution/Elimination"], "By using the elimination method, we find the values of x and y."))
            scenes.append(([f"x = {sol[x]}", f"y = {sol[y]}"], f"We get x equals {sol[x]} and y equals {sol[y]}."))
            build_video(scenes)
            return

    try:
        eq = sp.sympify(eq_string.replace("=", "-(") + ")")
        poly = sp.Poly(eq, x)
        coeffs = poly.all_coeffs()
        roots = sp.solve(eq, x)
    except Exception as e:
        print(f"Error: {e}")
        return

    # --- LINEAR EQUATION ---
    if len(coeffs) == 2: 
        left_str, right_str = eq_string.split("=")
        lhs_expr = sp.sympify(left_str)
        rhs_expr = sp.sympify(right_str)
        lhs_const = lhs_expr.subs(x, 0)
        lhs_x_coeff = sp.diff(lhs_expr, x) 
        
        scenes.append(([f"Solve: {format_screen(eq_string)}"], f"Let us solve the linear equation {format_voice(eq_string)}."))
        
        if lhs_const > 0:
            scenes.append(([f"Step 1: Transpose +{lhs_const}", f"⇒ {lhs_x_coeff}x = {format_screen(right_str)} - {lhs_const}"], 
                           f"First, transpose plus {lhs_const} to the right side. It becomes minus {lhs_const}."))
        elif lhs_const < 0:
            scenes.append(([f"Step 1: Transpose {lhs_const}", f"⇒ {lhs_x_coeff}x = {format_screen(right_str)} + {abs(lhs_const)}"], 
                           f"First, transpose minus {abs(lhs_const)} to the right side. It becomes plus {abs(lhs_const)}."))
        else:
            scenes.append(([f"Step 1: No constant to transpose"], "There is no constant on the left side to transpose."))
            
        new_rhs = rhs_expr - lhs_const
        scenes.append(([f"⇒ {lhs_x_coeff}x = {new_rhs}"], 
                       f"After simplifying, we get {lhs_x_coeff} x equals {new_rhs}."))
        
        root = roots[0]
        if lhs_x_coeff != 1:
            scenes.append(([f"Step 2: Divide both sides by {lhs_x_coeff}", f"⇒ x = {new_rhs} / {lhs_x_coeff}", f"⇒ x = {root}"], 
                           f"Now, divide both sides by {lhs_x_coeff}. Therefore, x equals {root}."))
        else:
            scenes.append(([f"⇒ x = {root}"], f"Therefore, x equals {root}."))
            
        build_video(scenes)

    # --- QUADRATIC EQUATION ---
    elif len(coeffs) == 3: 
        a, b, c = coeffs
        scenes.append(([f"Solve: {format_screen(eq_string)}"], f"We are now going to solve {format_voice(eq_string)}."))
        scenes.append((["General form:", "ax² + bx + c = 0"], "Comparing with the general form."))
        scenes.append(([f"a = {a}  b = {b}  c = {c}"], f"Here a is {a}, b is {b}, and c is {c}."))
        
        ac = a * c
        scenes.append(([f"Product of a and c: {a} × {c} = {ac}"], f"The product of a and c is {ac}."))
        
        # --- DYNAMIC SPLITTING THE MIDDLE TERM ---
        factors = sp.divisors(ac)
        num1, num2 = None, None
        
        for f in factors:
            if f + (ac // f) == b:
                num1, num2 = f, ac // f
                break
            if -f + -(ac // f) == b:
                num1, num2 = -f, -(ac // f)
                break
                
        if num1 is not None and num2 is not None:
            s_num1 = f"({num1})" if num1 < 0 else str(num1)
            s_num2 = f"({num2})" if num2 < 0 else str(num2)
            
            scenes.append(([f"Numbers that multiply to {ac}", f"and add to {b}:", f"{s_num1} × {s_num2} = {ac}", f"{s_num1} + {s_num2} = {b}"], 
                           f"We need two numbers that multiply to {ac} and add to {b}. They are {num1} and {num2}."))
            
            i_a, i_num1, i_num2, i_c = int(a), int(num1), int(num2), int(c)
            
            def fmt(n): return f"+ {n}" if n >= 0 else f"- {abs(n)}"
            def fmt_voice(n): return f"plus {n}" if n >= 0 else f"minus {abs(n)}"
            
            # 1. Splitting the middle term
            split_eq_screen = f"{i_a}x² {fmt(i_num1)}x {fmt(i_num2)}x {fmt(i_c)} = 0"
            split_eq_voice = f"Split the middle term: {i_a} x squared {fmt_voice(i_num1)} x {fmt_voice(i_num2)} x {fmt_voice(i_c)} equals zero."
            scenes.append((["Splitting the middle term:", format_screen(split_eq_screen)], split_eq_voice))
            
            # 2. Taking common (Clean Manual Logic)
            remaining_1 = sp.simplify((a*x**2 + num1*x) / x)
            common_2 = sp.simplify((num2*x + c) / remaining_1)
            
            rem_1_str = format_screen(str(remaining_1))
            c2_int = int(common_2)
            g2_str = f"- {abs(c2_int)}" if c2_int < 0 else f"+ {c2_int}"
            
            common_screen = f"x({rem_1_str}) {g2_str}({rem_1_str}) = 0"
            common_voice = f"Now, take the common factors out. We get x times {format_voice(str(remaining_1))}, {fmt_voice(c2_int)} times {format_voice(str(remaining_1))} equals zero."
            
            scenes.append((["Taking common:", f"⇒ {common_screen}"], common_voice))
            
            # 3. Final Factored Form
            factored_eq = sp.factor(eq)
            factored_str = format_screen(str(factored_eq))
            scenes.append((["Grouping and factorising:", f"⇒ {factored_str} = 0"], 
                           f"By grouping, we get {format_voice(str(factored_eq))} equals zero."))
            
            # 4. Either / Or Step
            r1, r2 = roots[0], roots[1]
            f1, f2 = factored_eq.args if len(factored_eq.args) == 2 else (factored_eq, 1)
            
            # Build the Either/Or text (e.g., x - 3 = 0 or 3x - 2 = 0)
            eq1_screen = f"{format_screen(str(f1))} = 0"
            eq2_screen = f"{format_screen(str(f2))} = 0"
            
            # Clean up text (e.g., if it's just "x", it becomes "x = 0")
            if eq1_screen.strip() == "x": eq1_screen = "x = 0"
            if eq2_screen.strip() == "x": eq2_screen = "x = 0"
            
            either_screen = f"Either {eq1_screen}   or   {eq2_screen}"
            either_voice = f"Either {format_voice(str(f1))} equals zero, or {format_voice(str(f2))} equals zero."
            
            scenes.append((["Either / Or:", either_screen], either_voice))
            
            # 5. Final Answers
            ans_screen = f"⇒ x = {format_screen(str(r1))}   or   x = {format_screen(str(r2))}"
            ans_voice = f"Therefore, x equals {format_voice(str(r1))} or x equals {format_voice(str(r2))}."
            scenes.append((["Final Answer:", ans_screen], ans_voice))
            
        else:
            factored_eq = sp.factor(eq)
            factored_str = format_screen(str(factored_eq))
            scenes.append((["Factorising the equation:", f"⇒ {factored_str} = 0"], 
                           f"By factorising the equation, we get {format_voice(str(factored_eq))} equals zero."))

        build_video(scenes)

def build_video(scenes):
    print("Generating Audio and Frames...")
    video_parts = []
    current_board = []
    
    for i, (new_lines, voice_text) in enumerate(scenes):
        print(f"   Processing Scene {i+1}...")
        if len(current_board) + len(new_lines) > 10: 
            current_board = []
        current_board.extend(new_lines)
        
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

    final_cmd = [FFMPEG_PATH, "-y", "-f", "concat", "-safe", "0", "-i", "temp_frames/concat.txt", "-c", "copy", "sample_lesson.mp4"]
    if run_ffmpeg(final_cmd): print("\nSUCCESS! Video generated.")

if __name__ == "__main__":
    main()