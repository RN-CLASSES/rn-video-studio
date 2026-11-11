"""Turn an uploaded photo / PDF into text. Claude vision is used when a key is
configured (it reads maths symbols far better); Tesseract is the fallback."""
import base64
import io

from PIL import Image

from . import config
from .solver import ProblemError


def _pdf_text(data: bytes) -> str:
    import pdfplumber
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        return "\n".join((p.extract_text() or "") for p in pdf.pages[:2]).strip()


def _vision(png: bytes) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY, timeout=40)
    msg = client.messages.create(
        model=config.LLM_MODEL, max_tokens=400,
        messages=[{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64", "media_type": "image/png",
                                         "data": base64.b64encode(png).decode()}},
            {"type": "text", "text": "Transcribe the maths/science question in this image as plain text "
                                     "(write powers like x^2, fractions like 1/2). Output only the question."}]}])
    return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip()


def extract_text(data: bytes, filename: str) -> str:
    if len(data) > config.MAX_UPLOAD_MB * 1024 * 1024:
        raise ProblemError(f"File is too large (max {config.MAX_UPLOAD_MB} MB).")
    name = (filename or "").lower()
    try:
        if name.endswith(".pdf"):
            text = _pdf_text(data)
        elif name.endswith((".png", ".jpg", ".jpeg", ".webp")):
            img = Image.open(io.BytesIO(data))
            img.verify()
            img = Image.open(io.BytesIO(data)).convert("RGB")
            img.thumbnail((1800, 1800))
            buf = io.BytesIO()
            img.save(buf, "PNG")
            text = ""
            if config.ANTHROPIC_API_KEY:
                try:
                    text = _vision(buf.getvalue())
                except Exception:
                    text = ""
            if not text:
                import pytesseract
                text = pytesseract.image_to_string(img).strip()
        else:
            raise ProblemError("Please upload a PNG, JPG or PDF file.")
    except ProblemError:
        raise
    except Exception:
        raise ProblemError("I could not read that file. Try a clearer photo, or type the problem.")
    if not text:
        raise ProblemError("I could not find any text in that file. Try a clearer photo, or type the problem.")
    return " ".join(text.split())[: config.MAX_TEXT_CHARS * 2]
