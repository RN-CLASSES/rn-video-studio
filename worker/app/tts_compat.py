"""Drop-in stand-in for `edge_tts` so the older topic scripts (mirror, trig,
chemistry, ...) use the same safe speech code without being rewritten."""
import asyncio

from . import tts


class Communicate:
    def __init__(self, text, voice=None, *a, **k):
        self.text = text

    async def save(self, filename):
        await asyncio.to_thread(tts.synth, self.text, filename)
