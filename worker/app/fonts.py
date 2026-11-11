"""Cross-platform font loader. Old scripts asked for Windows-only fonts
(arial.ttf, arialbd.ttf, seguisym.ttf). This maps those names to fonts that
exist on Linux/Docker (DejaVu has the maths symbols such as ⇒ ² ³ √ π)."""
from pathlib import Path
from PIL import ImageFont

_DIRS = [
    Path(__file__).parent / "assets" / "fonts",
    Path("/usr/share/fonts/truetype/dejavu"),
    Path("/usr/share/fonts/dejavu"),
    Path("/usr/local/share/fonts"),
    Path("C:/Windows/Fonts"),
    Path("/Library/Fonts"),
    Path("/System/Library/Fonts/Supplemental"),
]
_REGULAR = ["DejaVuSans.ttf", "seguisym.ttf", "arial.ttf", "Arial.ttf"]
_BOLD = ["DejaVuSans-Bold.ttf", "arialbd.ttf", "Arial Bold.ttf", "arial.ttf"]


def _find(candidates):
    for d in _DIRS:
        for name in candidates:
            p = d / name
            if p.exists():
                return str(p)
    return None


def truetype(name: str = "regular", size: int = 40):
    bold = "bd" in name.lower() or "bold" in name.lower()
    path = _find(_BOLD if bold else _REGULAR)
    if path:
        return ImageFont.truetype(path, size)
    try:  # last resort: let Pillow search by name
        return ImageFont.truetype("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf", size)
    except OSError:
        return ImageFont.load_default()
