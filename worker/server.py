from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import subprocess
import os
import re
import requests
import pdfplumber
import io
from PIL import Image
import pytesseract

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class VideoRequest(BaseModel):
    subject: str
    topic: str

def clean_math_text(text: str):
    text = text.replace("²", "**2").replace("³", "**3")
    text = text.replace("−", "-").replace("–", "-").replace("×", "*").replace("÷", "/")
    text = text.replace(" ", "") 
    text = re.sub(r'(\d)([a-zA-Z])', r'\1*\2', text)
    return text

def extract_text_from_file(file_bytes: bytes, filename: str):
    text = ""
    if filename.endswith(".pdf"):
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                text += page.extract_text() + "\n"
    elif filename.endswith((".png", ".jpg", ".jpeg")):
        img = Image.open(io.BytesIO(file_bytes))
        text = pytesseract.image_to_string(img)
    return text.strip()

def route_with_ai(text_input: str):
    url = "http://localhost:11434/api/generate"
    prompt = (
        f"Analyze this text: '{text_input}'\n"
        "1. If it is a math equation (like 2x + 5 = 15), output: MATH|equation\n"
        "2. If it is a speed/distance/time word problem, output: SPEED|distance|time\n"
        "3. If it is a mirror problem, output: MIRROR|concave_or_convex|object_position\n"
        "4. If it is general science text, output: SCIENCE|topic\n"
        "Output ONLY the result string. Do not explain."
    )
    try:
        response = requests.post(url, json={"model": "llama3.2", "prompt": prompt, "stream": False})
        ai_reply = response.json()['response'].strip()
        return ai_reply
    except Exception as e:
        return None

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    contents = await file.read()
    extracted_text = extract_text_from_file(contents, file.filename)
    
    if not extracted_text:
        return {"status": "error", "message": "Could not read text from file."}

    ai_decision = route_with_ai(extracted_text)
    if not ai_decision:
        return {"status": "error", "message": "AI failed to analyze the question."}

    if os.path.exists("sample_lesson.mp4"): os.remove("sample_lesson.mp4")
    if os.path.exists("word_problem.mp4"): os.remove("word_problem.mp4")
    if os.path.exists("spherical_mirror.mp4"): os.remove("spherical_mirror.mp4")
    
    if "MATH|" in ai_decision:
        eq = clean_math_text(ai_decision.split("|")[1])
        subprocess.run(["python", "render.py", eq], capture_output=True, text=True)
        video_file = "sample_lesson.mp4"
    elif "SPEED|" in ai_decision:
        parts = ai_decision.split("|")
        subprocess.run(["python", "word_problem.py", "speed", parts[1].strip(), parts[2].strip()], capture_output=True, text=True)
        video_file = "word_problem.mp4"
    elif "MIRROR|" in ai_decision:
        parts = ai_decision.split("|")
        subprocess.run(["python", "spherical_mirror.py", parts[1].strip(), parts[2].strip()], capture_output=True, text=True)
        video_file = "spherical_mirror.mp4"
    else:
        return {"status": "error", "message": "Topic not supported yet by our video engines."}

    if not os.path.exists(video_file):
        return {"status": "error", "message": "Video generation failed."}
        
    return {"status": "success", "video_url": video_file}


@app.post("/generate")
def generate_video(req: VideoRequest):
    if os.path.exists("sample_lesson.mp4"): os.remove("sample_lesson.mp4")
    if os.path.exists("science_lesson.mp4"): os.remove("science_lesson.mp4")
    if os.path.exists("reflection_lesson.mp4"): os.remove("reflection_lesson.mp4")
    if os.path.exists("word_problem.mp4"): os.remove("word_problem.mp4")
    if os.path.exists("spherical_mirror.mp4"): os.remove("spherical_mirror.mp4")
    if os.path.exists("trig_balloon.mp4"): os.remove("trig_balloon.mp4")
    if os.path.exists("covalent_bonds.mp4"): os.remove("covalent_bonds.mp4")
        
    if req.subject == "speed":
        result = subprocess.run(["python", "science.py", req.topic], capture_output=True, text=True)
        video_file = "science_lesson.mp4"
    elif req.subject == "reflection":
        result = subprocess.run(["python", "reflection.py"], capture_output=True, text=True)
        video_file = "reflection_lesson.mp4"
    elif req.subject == "mirror_concave":
        result = subprocess.run(["python", "spherical_mirror.py", "concave", req.topic], capture_output=True, text=True)
        video_file = "spherical_mirror.mp4"
    elif req.subject == "mirror_convex":
        result = subprocess.run(["python", "spherical_mirror.py", "convex", "between_infinity_pole"], capture_output=True, text=True)
        video_file = "spherical_mirror.mp4"
    elif req.subject == "trig_balloon":
        result = subprocess.run(["python", "math_trig.py"], capture_output=True, text=True)
        video_file = "trig_balloon.mp4"
    elif req.subject == "chem_covalent":
        result = subprocess.run(["python", "chem_covalent.py"], capture_output=True, text=True)
        video_file = "covalent_bonds.mp4"
    else: 
        math_topic = clean_math_text(req.topic)
        if "=" not in math_topic:
            ai_decision = route_with_ai(req.topic)
            if ai_decision and "SPEED|" in ai_decision:
                parts = ai_decision.split("|")
                result = subprocess.run(["python", "word_problem.py", "speed", parts[1].strip(), parts[2].strip()], capture_output=True, text=True)
                video_file = "word_problem.mp4"
            else:
                return {"status": "error", "message": "Could not understand the math problem."}
        else:
            result = subprocess.run(["python", "render.py", math_topic], capture_output=True, text=True)
            video_file = "sample_lesson.mp4"
    
    if result.returncode != 0 or not os.path.exists(video_file):
        return {"status": "error", "message": "Video file was not created."}
        
    return {"status": "success", "video_url": video_file}

app.mount("/video", StaticFiles(directory=".", html=False), name="video")