"""One video engine for every maths topic.

A topic only has to produce a list of `Scene`s (what to show + what to say).
`build_video` turns them into an MP4 using Pillow + ffmpeg.
"""
import os
import subprocess
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from PIL import Image, ImageDraw

from . import config, fonts, tts

WIDTH, HEIGHT = 1280, 720
BG_TOP, BG_BOTTOM = (22, 32, 46), (34, 48, 66)
TEXT = (255, 255, 255)
HIGHLIGHT = (255, 200, 0)
ANSWER = (110, 231, 160)
MUTED = (140, 155, 175)
HEADINGS = ("step", "given", "formula", "method", "solve", "final answer", "answer",
            "roots", "either", "check", "note", "result")
MAX_BOARD_LINES = 9


@dataclass
class Scene:
    lines: List[str]                     # lines added to the board
    voice: str                           # what the teacher says
    clear: bool = False                  # start a fresh board first
    answer: bool = False                 # draw these lines in "answer" colour


@dataclass
class Board:
    items: list = field(default_factory=list)   # (text, kind)

    def add(self, lines, answer=False):
        for ln in lines:
            kind = "heading" if _is_heading(ln) else ("answer" if answer else "text")
            self.items.append((ln, kind))


def _is_heading(line: str) -> bool:
    low = line.strip().lower()
    return low.endswith(":") or low.startswith(HEADINGS)


def _gradient() -> Image.Image:
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_TOP)
    px = ImageDraw.Draw(img)
    for y in range(HEIGHT):
        t = y / HEIGHT
        c = tuple(int(BG_TOP[i] + (BG_BOTTOM[i] - BG_TOP[i]) * t) for i in range(3))
        px.line([(0, y), (WIDTH, y)], fill=c)
    return img


_BG = None


def draw_board(items, path: str, title: str = ""):
    global _BG
    if _BG is None:
        _BG = _gradient()
    img = _BG.copy()
    d = ImageDraw.Draw(img)
    f_small = fonts.truetype("regular", 22)
    if title:
        d.text((50, 28), title, font=f_small, fill=MUTED)
    d.text((WIDTH - 50, 28), "RN Classes", font=f_small, fill=MUTED, anchor="ra")

    n = max(len(items), 1)
    line_h = 64 if n <= 8 else 54
    y = 110 + max(0, (8 - n)) * 14           # roughly vertically centred
    max_w = WIDTH - 140
    for text, kind in items:
        size = 40
        font_name = "bold" if kind == "heading" else "regular"
        font = fonts.truetype(font_name, size)
        while d.textlength(text, font=font) > max_w and size > 22:   # shrink to fit
            size -= 2
            font = fonts.truetype(font_name, size)
        color = {"heading": HIGHLIGHT, "answer": ANSWER}.get(kind, TEXT)
        if kind == "answer":
            w = d.textlength(text, font=font)
            d.rounded_rectangle([(WIDTH - w) / 2 - 24, y - 8, (WIDTH + w) / 2 + 24, y + size + 14],
                                radius=14, outline=ANSWER, width=3)
        d.text((WIDTH / 2, y), text, font=font, fill=color, anchor="ma")
        y += line_h
    img.save(path)


def _ffmpeg(cmd: List[str]):
    r = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    if r.returncode != 0:
        raise RuntimeError("ffmpeg failed: " + r.stderr[-400:])


def build_video(scenes: List[Scene], out_path: str, workdir: str, title: str = "",
                progress: Optional[Callable[[int, str], None]] = None) -> str:
    os.makedirs(workdir, exist_ok=True)
    board = Board()
    clips = []
    total = len(scenes)
    for i, sc in enumerate(scenes):
        if progress:
            progress(5 + int(85 * i / total), f"Recording step {i + 1} of {total}")
        if sc.clear or len(board.items) + len(sc.lines) > MAX_BOARD_LINES:
            board = Board()
        board.add(sc.lines, answer=sc.answer)

        audio = os.path.join(workdir, f"s{i}.mp3")
        png = os.path.join(workdir, f"s{i}.png")
        clip = os.path.join(workdir, f"c{i}.mp4")
        length = tts.synth(sc.voice, audio)
        draw_board(board.items, png, title)
        _ffmpeg([config.FFMPEG, "-y", "-loop", "1", "-framerate", "24", "-i", png, "-i", audio,
                 "-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p", "-r", "24",
                 "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "2",
                 "-af", "apad=pad_dur=0.6", "-t", f"{length + 0.6:.2f}", clip])
        clips.append(clip)

    if progress:
        progress(93, "Joining the video")
    listing = os.path.join(workdir, "concat.txt")
    with open(listing, "w") as fh:
        for c in clips:
            fh.write(f"file '{os.path.abspath(c)}'\n")
    _ffmpeg([config.FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", listing,
             "-c", "copy", "-movflags", "+faststart", out_path])
    return out_path
