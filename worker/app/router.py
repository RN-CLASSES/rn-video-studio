"""Works out what kind of problem the student typed.

1. Obvious maths (contains '=' and x/y) is handled with no AI at all.
2. Otherwise Claude (if ANTHROPIC_API_KEY is set) reads the problem and answers
   with strict JSON, which is validated before use.
3. Without a key we fall back to keyword rules for the built-in lessons.
"""
import json
import re
from typing import Optional

from . import config
from .solver import ProblemError, parse_equations

# Ready-made animated lessons (older scripts): key -> (script, output file)
LESSONS = {
    "trig_balloon": ("math_trig.py", "trig_balloon.mp4", "Trigonometry: height of a balloon"),
    "covalent_bonds": ("chem_covalent.py", "covalent_bonds.mp4", "Chemistry: covalent bonds"),
    "reflection": ("reflection.py", "reflection_lesson.mp4", "Physics: reflection of light"),
    "science_lesson": ("science.py", "science_lesson.mp4", "Science lesson"),
    "mirror_convex": ("spherical_mirror.py", "spherical_mirror.mp4", "Convex mirror image formation"),
    "mirror_concave": ("spherical_mirror.py", "spherical_mirror.mp4", "Concave mirror image formation"),
}

KEYWORDS = [
    (r"convex", "mirror_convex"), (r"concave", "mirror_concave"),
    (r"mirror", "mirror_concave"), (r"reflect", "reflection"),
    (r"covalent|bond", "covalent_bonds"),
    (r"balloon|angle of elevation|trigonom|tan\s*\d|sin\s*\d|cos\s*\d", "trig_balloon"),
]

PROMPT = """You classify school maths/science questions for a video generator.
Reply with ONE JSON object and nothing else. Choose exactly one form:
{"type":"equation","equations":["2x + 5 = 15"]}            (one equation in x, or two equations in x and y; write them in plain text)
{"type":"speed","distance":150,"time":3,"speed":null,"dist_unit":"km","time_unit":"h"}   (exactly two of the three numbers given, the unknown is null)
{"type":"lesson","key":"<one of: %s>"}   (only if the question is about that built-in topic)
{"type":"unsupported","reason":"short reason"}
For word problems that lead to an equation, set up the equation yourself, e.g. "A number plus 5 is 12" -> {"type":"equation","equations":["x + 5 = 12"]}.
Question: """ % ", ".join(LESSONS)


def _parses_as_equation(t: str) -> bool:
    if "=" not in t:
        return False
    try:
        parse_equations(t)
        return True
    except ProblemError:
        return False


def _llm(text: str) -> Optional[dict]:
    if not config.ANTHROPIC_API_KEY:
        return None
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY, timeout=30)
        msg = client.messages.create(model=config.LLM_MODEL, max_tokens=300,
                                     messages=[{"role": "user", "content": PROMPT + text}])
        raw = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
        m = re.search(r"\{.*\}", raw, re.S)
        return json.loads(m.group(0)) if m else None
    except Exception:
        return None


_N = r"(\d+(?:\.\d+)?)"
_DIST = re.compile(_N + r"\s*(km|kilometers?|kilometres?|meters?|metres?|miles?|m|cm)\b(?!\s*(?:/|per\b|ph\b))", re.I)
_TIME = re.compile(_N + r"\s*(hours?|hrs?|h|minutes?|mins?|seconds?|secs?|s)\b(?!\s*/)", re.I)
_SPEED = re.compile(_N + r"\s*(km/h|km/hr|kmph|kph|m/s|km per hour|miles per hour|mph|m per s(?:ec(?:ond)?)?)", re.I)
_DU = {"km": "km", "kilometer": "km", "kilometre": "km", "meter": "m", "metre": "m", "mile": "mi", "m": "m", "cm": "cm"}
_TU = {"h": "h", "hr": "h", "hour": "h", "min": "min", "minute": "min", "s": "s", "sec": "s", "second": "s"}


def _unit(raw: str, table: dict) -> str:
    u = raw.lower().rstrip("s") if raw.lower() not in ("s", "m") else raw.lower()
    return table.get(u, table.get(u.rstrip("s"), u))


def _speed_rules(text: str) -> Optional[dict]:
    """Free, offline reader for plain 'distance / time / speed' problems."""
    if not re.search(r"speed|velocity|distance|travel|how far|how long|how fast|km|mph", text, re.I):
        return None
    d, t, v = _DIST.search(text), _TIME.search(text), _SPEED.search(text)
    found = [m for m in (d, t, v) if m]
    if len(found) != 2:
        return None
    spec = {"type": "speed", "distance": None, "time": None, "speed": None, "dist_unit": "km", "time_unit": "h"}
    if d:
        spec["distance"], spec["dist_unit"] = float(d.group(1)), _unit(d.group(2), _DU)
    if t:
        spec["time"], spec["time_unit"] = float(t.group(1)), _unit(t.group(2), _TU)
    if v:
        spec["speed"] = float(v.group(1))
        su = v.group(2).lower()
        if su.startswith("m/s") or su.startswith("m per s"):
            du, tu = "m", "s"
        elif su in ("mph", "miles per hour"):
            du, tu = "mi", "h"
        else:
            du, tu = "km", "h"
        if (d and spec["dist_unit"] != du) or (t and spec["time_unit"] != tu):
            return None                     # mixed units: let the AI (or the student) sort it out
        spec["dist_unit"], spec["time_unit"] = du, tu
    return spec


def _num(v):
    if v is None:
        return None
    try:
        f = float(v)
        return f if f == f and abs(f) < 1e12 else None
    except (TypeError, ValueError):
        return None


def _validate(spec: dict) -> dict:
    t = spec.get("type")
    if t == "equation":
        eqs = spec.get("equations")
        if isinstance(eqs, list) and 1 <= len(eqs) <= 2 and all(isinstance(e, str) for e in eqs):
            return {"type": "equation", "text": "; ".join(eqs)}
    elif t == "speed":
        vals = [_num(spec.get(k)) for k in ("distance", "time", "speed")]
        if sum(v is not None for v in vals) == 2:
            return {"type": "speed", "distance": vals[0], "time": vals[1], "speed": vals[2],
                    "dist_unit": str(spec.get("dist_unit") or "km")[:4],
                    "time_unit": str(spec.get("time_unit") or "h")[:4]}
    elif t == "lesson" and spec.get("key") in LESSONS:
        return {"type": "lesson", "key": spec["key"]}
    elif t == "unsupported":
        raise ProblemError(str(spec.get("reason") or "This type of problem is not supported yet.")[:200])
    raise ProblemError("I could not understand this problem. Try typing the equation, like 2x + 5 = 15.")


def classify(text: str) -> dict:
    text = (text or "").strip()
    if not text:
        raise ProblemError("Please type or upload a problem.")
    if len(text) > config.MAX_TEXT_CHARS:
        raise ProblemError("That problem is too long. Please keep it under %d characters." % config.MAX_TEXT_CHARS)

    if text in LESSONS:                       # chosen from the topic list
        return {"type": "lesson", "key": text}
    if _parses_as_equation(text):             # no AI needed for plain equations
        return {"type": "equation", "text": text}

    rule = _speed_rules(text)
    if rule:
        return rule

    spec = _llm(text)
    if spec:
        return _validate(spec)

    low = text.lower()
    for pattern, key in KEYWORDS:
        if re.search(pattern, low):
            return {"type": "lesson", "key": key}
    raise ProblemError("I could not understand this problem. Type an equation like 2x + 5 = 15"
                       + ("" if config.ANTHROPIC_API_KEY else ", or ask the site owner to enable AI reading of word problems."))
