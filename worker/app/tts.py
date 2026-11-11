"""Text-to-speech with a safety net.
Uses Microsoft Edge voices (free). If the voice service is unreachable the
video is still produced, with silent audio timed to the text, so a network
hiccup never breaks a job."""
import asyncio
import subprocess

from mutagen.mp3 import MP3

from . import config


def _silent_mp3(path: str, seconds: float):
    subprocess.run(
        [config.FFMPEG, "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
         "-t", f"{seconds:.2f}", "-c:a", "libmp3lame", "-b:a", "48k", path],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)


async def _edge(text: str, path: str):
    import edge_tts
    await asyncio.wait_for(edge_tts.Communicate(text, config.VOICE).save(path), timeout=40)


def synth(text: str, path: str) -> float:
    """Write an mp3 for `text` to `path`; return its length in seconds."""
    for _ in range(2):
        try:
            asyncio.run(_edge(text, path))
            length = MP3(path).info.length
            if length > 0.2:
                return length
        except Exception:
            pass
    seconds = max(1.8, len(text.split()) * 0.42)
    _silent_mp3(path, seconds)
    return seconds
