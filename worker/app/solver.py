"""Step-by-step solvers. Sympy does all the maths (so answers are right);
this file only decides how to *teach* it.

Supported: linear equations (x on both sides, brackets, fractions),
quadratics (split-the-middle-term, square roots, quadratic formula incl.
repeated/complex roots), pairs of linear equations (elimination), higher
degree polynomials (factorise + roots) and speed/distance/time.
"""
import re
from typing import List, Optional, Tuple

import sympy as sp
from sympy.parsing.sympy_parser import (convert_xor, implicit_multiplication_application,
                                        parse_expr, standard_transformations)

from .engine import Scene

x, y = sp.symbols("x y")
TRANSFORMS = standard_transformations + (implicit_multiplication_application, convert_xor)
ALLOWED_NAMES = {"x", "y", "sqrt", "pi", "sin", "cos", "tan", "log", "ln", "exp", "abs"}
NS = {"x": x, "y": y, "pi": sp.pi, "ln": sp.log}


class ProblemError(Exception):
    """A problem we cannot (yet) solve; the message is shown to the student."""


# ----------------------------------------------------------------- parsing --
def normalise(text: str) -> str:
    t = text.strip()
    t = t.replace("²", "**2").replace("³", "**3").replace("^", "**")
    t = t.replace("−", "-").replace("–", "-").replace("—", "-")
    t = t.replace("×", "*").replace("·", "*").replace("⋅", "*").replace("÷", "/")
    t = t.replace("π", "pi").replace("＝", "=")
    t = re.sub(r"√\s*\(", "sqrt(", t)
    t = re.sub(r"√\s*([0-9.]+|[a-zA-Z])", r"sqrt(\1)", t)
    t = re.sub(r"^\s*(please\s+)?(solve|find( the value of)?( [xy])?|simplify)\b\s*[:,-]?\s*", "", t, flags=re.I)
    t = re.sub(r"^\s*(q(uestion)?\.?\s*)?\d+[.)]\s+", "", t, flags=re.I)
    return t.strip().rstrip(".")


def _safe_parse(s: str) -> sp.Expr:
    s = s.strip()
    if not s or len(s) > 200:
        raise ProblemError("The expression is empty or too long.")
    if re.search(r"[^0-9a-zA-Z+\-*/().,\s]", s):
        raise ProblemError("I can only read numbers, x, y and + - × ÷ ^ ( ) in equations.")
    for word in re.findall(r"[A-Za-z]+", s):
        if word not in ALLOWED_NAMES and not set(word) <= {"x", "y"}:
            raise ProblemError(f"I don't understand '{word}' in this equation.")
    if re.search(r"\d{10,}", s):
        raise ProblemError("Those numbers are too large.")
    # Powers: a plain whole number up to 99, never chained (x**2**3), and at most four per side.
    # This stops 9**9**9**9 style input from freezing the server.
    exps = re.findall(r"\*\*\s*([^\s+\-*/]*)", s)
    if (len(exps) > 4
            or any(not re.fullmatch(r"\(?\d{1,2}\)?", e) for e in exps)
            or re.search(r"\*\*\s*\(?\d+\)?\s*\*\*", s)
            or re.search(r"\)\s*\*\*", s) and len(exps) > 1):
        raise ProblemError("I can only handle simple whole-number powers like x² or x^3.")
    try:
        return sp.sympify(parse_expr(s, local_dict=NS, transformations=TRANSFORMS))
    except Exception:
        raise ProblemError("I could not read that equation. Try writing it like 2x + 5 = 15.")


def parse_equations(text: str) -> List[Tuple[sp.Expr, sp.Expr]]:
    t = normalise(text)
    parts = [p for p in re.split(r";|\n|\band\b|,(?=[^=]*=)", t) if p.strip()]
    eqs = []
    for p in parts:
        if p.count("=") != 1:
            raise ProblemError("Each equation needs exactly one '=' sign.")
        l, r = p.split("=")
        eqs.append((_safe_parse(l), _safe_parse(r)))
    if not eqs or len(eqs) > 2:
        raise ProblemError("I can solve one equation, or two equations together.")
    return eqs


# -------------------------------------------------------------- formatting --
def pretty(e) -> str:
    s = sp.sstr(e)
    s = re.sub(r"\*\*2\b", "²", s)
    s = re.sub(r"\*\*3\b", "³", s)
    s = re.sub(r"\*\*(\d+)", r"^\1", s)
    s = s.replace("sqrt(", "√(")
    s = re.sub(r"√\((\w+)\)", r"√\1", s)
    s = re.sub(r"\bI\b", "i", s)
    s = re.sub(r"(?<=[\d.)])\*(?=[a-zA-Z(√])", "", s)
    s = re.sub(r"(?<=[a-zA-Z²³)])\*(?=[a-zA-Z(√])", "", s)
    s = s.replace("*", "×")
    s = re.sub(r"(?<=[\w)²³])\s*([+\-])\s*(?=[\w(√])", r" \1 ", s)
    return s.strip()


def speak(s: str) -> str:
    s = pretty(s) if not isinstance(s, str) else s
    s = s.replace("²", " squared ").replace("³", " cubed ").replace("√", " square root of ")
    s = re.sub(r"\^(\d+)", r" to the power \1 ", s)
    s = s.replace(" - ", " minus ").replace(" + ", " plus ").replace("×", " times ")
    s = re.sub(r"(^|[(])-", r"\1 minus ", s)
    s = s.replace("/", " over ").replace("=", " equals ").replace("(", " ").replace(")", " ")
    s = re.sub(r"(\d)([a-zA-Z])", r"\1 \2", s)
    s = s.replace("±", " plus or minus ")
    return " ".join(s.split())


def eq_str(l, r) -> str:
    return f"{pretty(l)} = {pretty(r)}"


def add_term(first, other) -> str:
    """'first + other' / 'first - other' with correct signs."""
    other = sp.sympify(other)
    if other.could_extract_minus_sign():
        return f"{pretty(first)} + {pretty(-other)}"
    return f"{pretty(first)} - {pretty(other)}"


def root_str(r) -> str:
    return pretty(sp.simplify(r))


def sci(var: str, value) -> str:
    return f"{var} = {root_str(value)}"


# ------------------------------------------------------------------ linear --
def solve_linear(lhs, rhs) -> List[Scene]:
    S: List[Scene] = []
    given = eq_str(lhs, rhs)
    S.append(Scene(["Solve:", given], f"Let us solve the equation {speak(given)}."))
    L, R = sp.expand(lhs), sp.expand(rhs)
    if (pretty(L), pretty(R)) != (pretty(lhs), pretty(rhs)):
        S.append(Scene(["Step 1: Open the brackets", f"⇒ {eq_str(L, R)}"],
                       f"First, simplify both sides. We get {speak(eq_str(L, R))}."))
    a, b = L.coeff(x, 1), L.subs(x, 0)
    c, d = R.coeff(x, 1), R.subs(x, 0)

    if c != 0:
        left = add_term(a * x, -c * x)
        right = add_term(d, b) if b != 0 else pretty(d)
        S.append(Scene(["Take the x terms to the left and the numbers to the right:",
                        f"⇒ {left} = {right}"],
                       "Now take all the x terms to the left side and the numbers to the right side. "
                       "Remember, the sign changes when we transpose."))
        A, B = a - c, d - b
    elif b != 0:
        S.append(Scene([f"Step 1: Transpose {pretty(b)}", f"⇒ {pretty(a * x)} = {add_term(d, b)}"],
                       f"Transpose {speak(pretty(b))} to the right side. Its sign changes."))
        A, B = a, d - b
    else:
        A, B = a, d
    S.append(Scene([f"⇒ {pretty(A * x)} = {pretty(B)}"], f"This gives {speak(f'{pretty(A * x)} = {pretty(B)}')}."))

    if A == 0:
        if B == 0:
            S.append(Scene(["Both sides are always equal:", "Infinitely many solutions"],
                           "Both sides are identical, so every value of x satisfies this equation.", answer=True))
        else:
            S.append(Scene(["This can never be true:", "No solution"],
                           "This statement is never true, so the equation has no solution.", answer=True))
        return S

    root = sp.nsimplify(B / A)
    if A != 1:
        S.append(Scene([f"Step 2: Divide both sides by {pretty(A)}", f"⇒ x = {pretty(B)}/{pretty(A)}" if A != -1 else "⇒ x = -(" + pretty(B) + ")"],
                       f"Now divide both sides by {speak(pretty(A))}."))
    S.append(Scene(["Final Answer:", sci("x", root)], f"Therefore, x equals {speak(root_str(root))}.", answer=True))
    lv, rv = sp.simplify(lhs.subs(x, root)), sp.simplify(rhs.subs(x, root))
    S.append(Scene([f"Check: put x = {root_str(root)}", f"LHS = {pretty(lv)},  RHS = {pretty(rv)}  ✓"],
                   f"Let us check. Putting x equal to {speak(root_str(root))}, the left side is {speak(pretty(lv))} "
                   f"and the right side is {speak(pretty(rv))}. They are equal, so our answer is correct."))
    return S


# --------------------------------------------------------------- quadratic --
def _try_split(a: int, b: int, c: int):
    """Return (p, q_signed, B1, m, n) for grouping, or None."""
    ac = a * c
    cands = []
    for d in sp.divisors(abs(ac)):
        for m in (d, -d):
            n = ac // m
            if m + n == b:
                cands.append((m, n))
    for m, n in cands:
        p = sp.igcd(a, m)
        B1 = (a // p) * x + (m // p)
        q = sp.igcd(n, c)
        for s in (1, -1):
            if (n // (s * q)) * x + (c // (s * q)) == B1:
                factor = sp.expand((p * x + s * q) * B1 - (a * x**2 + b * x + c))
                if factor == 0:
                    return p, s * q, B1, m, n
    return None


def solve_quadratic(lhs, rhs) -> List[Scene]:
    S: List[Scene] = []
    given = eq_str(lhs, rhs)
    expr = sp.expand(lhs - rhs)
    S.append(Scene(["Solve:", given], f"We are going to solve the quadratic equation {speak(given)}."))
    if (pretty(sp.expand(lhs)), pretty(rhs)) != (pretty(expr), "0"):
        S.append(Scene(["Step 1: Write in standard form", f"⇒ {pretty(expr)} = 0"],
                       f"First, bring everything to one side. We get {speak(pretty(expr))} equals zero."))
    a, b, c = sp.Poly(expr, x).all_coeffs()

    dens = [sp.Rational(v).q for v in (a, b, c)]
    if any(dd != 1 for dd in dens):
        m = sp.ilcm(*dens)
        expr = sp.expand(expr * m)
        a, b, c = sp.Poly(expr, x).all_coeffs()
        S.append(Scene([f"Multiply every term by {m} to remove fractions", f"⇒ {pretty(expr)} = 0"],
                       f"Multiply every term by {m} to remove the fractions. We get {speak(pretty(expr))} equals zero."))
    if a < 0:
        expr = sp.expand(-expr)
        a, b, c = sp.Poly(expr, x).all_coeffs()
        S.append(Scene(["Multiply by -1 to make x² positive", f"⇒ {pretty(expr)} = 0"],
                       f"Multiply by minus one so the x squared term is positive. We get {speak(pretty(expr))} equals zero."))
    a, b, c = int(a), int(b), int(c)
    roots = sorted(sp.solve(expr, x), key=lambda r: (sp.im(r) != 0, sp.re(r)))
    if not roots:
        raise ProblemError("I could not find the roots of this equation.")

    S.append(Scene(["General form:", "ax² + bx + c = 0"], "Comparing with the general form a x squared plus b x plus c equals zero."))
    S.append(Scene([f"a = {a},  b = {b},  c = {c}"], f"Here a is {speak(str(a))}, b is {speak(str(b))}, and c is {speak(str(c))}."))

    answer_line = None
    if c == 0:  # ax² + bx = 0
        B1 = a * x + b
        S.append(Scene(["Take x common:", f"⇒ x({pretty(B1)}) = 0"],
                       f"There is no constant term, so take x common. We get x times {speak(pretty(B1))} equals zero."))
        S.append(Scene(["Either x = 0", f"or {pretty(B1)} = 0"],
                       f"Either x equals zero, or {speak(pretty(B1))} equals zero."))
        answer_line = " or ".join(sci("x", r) for r in roots)
    elif b == 0 and sp.sqrt(sp.Rational(-c, a)).is_real:
        k = sp.Rational(-c, a)
        S.append(Scene(["Step 2: Move the constant", f"⇒ {pretty(a * x**2)} = {pretty(-c)}"],
                       f"Move the constant to the right side. {speak(pretty(a * x**2))} equals {speak(pretty(-c))}."))
        if a != 1:
            S.append(Scene([f"⇒ x² = {pretty(k)}"], f"Divide both sides by {a}. x squared equals {speak(pretty(k))}."))
        S.append(Scene(["Take the square root of both sides:", f"⇒ x = ± {pretty(sp.sqrt(k))}"],
                       f"Taking the square root of both sides, x equals plus or minus {speak(pretty(sp.sqrt(k)))}."))
        answer_line = " or ".join(sci("x", r) for r in roots)
    else:
        split = _try_split(a, b, c) if b != 0 else None
        if split:
            p, q, B1, m, n = split
            ac = a * c
            S.append(Scene([f"Product of a and c: {a} × {c} = {ac}"], f"The product of a and c is {speak(str(ac))}."))
            sm, sn = (f"({m})" if m < 0 else str(m)), (f"({n})" if n < 0 else str(n))
            S.append(Scene([f"Find two numbers with product {ac} and sum {b}:", f"{sm} × {sn} = {ac}   and   {sm} + {sn} = {b}"],
                           f"We need two numbers whose product is {speak(str(ac))} and whose sum is {speak(str(b))}. They are {speak(str(m))} and {speak(str(n))}."))
            split_eq = f"{pretty(a * x**2)} {'+' if m > 0 else '-'} {pretty(abs(m) * x)} {'+' if n > 0 else '-'} {pretty(abs(n) * x)} {'+' if c > 0 else '-'} {abs(c)} = 0"
            S.append(Scene(["Split the middle term:", f"⇒ {split_eq}"], f"Split the middle term. We get {speak(split_eq)}."))
            first = (f"{pretty(p * x)}({pretty(B1)})" if p != 1 else f"x({pretty(B1)})")
            second = f"{abs(q)}({pretty(B1)})" if abs(q) != 1 else f"({pretty(B1)})"
            common = f"{first} {'+' if q > 0 else '-'} {second} = 0"
            S.append(Scene(["Take common factors from each pair:", f"⇒ {common}"],
                           f"Now take the common factor out of each pair. We get {speak(common)}."))
            f1 = p * x + q
            S.append(Scene(["Factorise:", f"⇒ ({pretty(f1)})({pretty(B1)}) = 0"],
                           f"Since {speak(pretty(B1))} is common, we get {speak(pretty(f1))} times {speak(pretty(B1))} equals zero."))
            S.append(Scene([f"Either {pretty(f1)} = 0", f"or {pretty(B1)} = 0"],
                           f"Either {speak(pretty(f1))} equals zero, or {speak(pretty(B1))} equals zero."))
            r1, r2 = sp.Rational(-q, p), sp.Rational(-B1.subs(x, 0), B1.coeff(x, 1))
            if r1 == r2:
                answer_line = sci("x", r1) + "  (repeated root)"
            else:
                answer_line = f"{sci('x', r1)}   or   {sci('x', r2)}"
        else:
            D = b * b - 4 * a * c
            S.append(Scene(["Use the quadratic formula:", "x = (-b ± √(b² - 4ac)) / 2a"],
                           "This does not factorise easily, so we use the quadratic formula. x equals minus b plus or minus the square root of b squared minus 4 a c, all over 2 a."))
            S.append(Scene(["Discriminant:", f"D = b² - 4ac = ({b})² - 4({a})({c}) = {D}"],
                           f"First find the discriminant. D equals {speak(str(D))}."))
            if D < 0:
                S.append(Scene(["D is negative, so there are", "no real roots (complex roots):"],
                               "The discriminant is negative, so there are no real roots. The roots are complex numbers."))
            elif D == 0:
                S.append(Scene(["D = 0, so the roots are equal"], "The discriminant is zero, so both roots are equal."))
            answer_line = " or ".join(sci("x", r) for r in roots)
            if D == 0:
                answer_line = sci("x", roots[0]) + "  (repeated root)"

    final_voice = "Therefore, " + " or ".join(f"x equals {speak(root_str(r))}" for r in dict.fromkeys(roots)) + "."
    S.append(Scene(["Final Answer:", "⇒ " + answer_line], final_voice, answer=True))
    return S


# ------------------------------------------------------------ higher degree --
def solve_polynomial(lhs, rhs) -> List[Scene]:
    expr = sp.expand(lhs - rhs)
    deg = sp.Poly(expr, x).degree()
    if deg > 4:
        raise ProblemError("I can solve equations up to degree 4 for now.")
    given = eq_str(lhs, rhs)
    fac = sp.factor(expr)
    roots = sp.solve(expr, x)
    S = [Scene(["Solve:", given], f"We are going to solve {speak(given)}."),
         Scene(["Factorise:", f"⇒ {pretty(fac)} = 0"], f"Factorising, we get {speak(pretty(fac))} equals zero.")]
    ans = " or ".join(sci("x", r) for r in roots)
    S.append(Scene(["Final Answer:", "⇒ " + ans], "Therefore, " + " or ".join(f"x equals {speak(root_str(r))}" for r in roots) + ".", answer=True))
    return S


# ----------------------------------------------------------------- systems --
def _lin(a, b, c) -> str:
    return f"{pretty(a * x + b * y)} = {pretty(c)}"


def solve_system(e1, e2) -> List[Scene]:
    rows = []
    for l, r in (e1, e2):
        ex = sp.expand(l - r)
        if sp.Poly(ex, x, y).total_degree() > 1:
            raise ProblemError("For two equations I can only solve linear ones (no x² or xy).")
        rows.append((ex.coeff(x, 1), ex.coeff(y, 1), -ex.subs({x: 0, y: 0})))
    (a1, b1, c1), (a2, b2, c2) = rows
    S = [Scene(["Given equations:", f"(1)  {_lin(a1, b1, c1)}", f"(2)  {_lin(a2, b2, c2)}"],
               f"We have two equations. Equation one: {speak(_lin(a1, b1, c1))}. Equation two: {speak(_lin(a2, b2, c2))}.")]
    det = a1 * b2 - a2 * b1
    if det == 0:
        consistent = (a1 * c2 - a2 * c1 == 0) and (b1 * c2 - b2 * c1 == 0)
        msg = "Infinitely many solutions" if consistent else "No solution"
        S.append(Scene(["The lines are parallel or identical:", msg],
                       "These two equations have the same slope, so there is no single pair of values." , answer=True))
        return S

    if b1 != 0 and b2 != 0:
        v, u = y, x
        pv1, pv2, pu1, pu2 = b1, b2, a1, a2
    elif a1 != 0 and a2 != 0:
        v, u = x, y
        pv1, pv2, pu1, pu2 = a1, a2, b1, b2
    else:
        sol = sp.solve([sp.Eq(a1 * x + b1 * y, c1), sp.Eq(a2 * x + b2 * y, c2)], [x, y])
        S.append(Scene(["Final Answer:", f"x = {pretty(sol[x])},  y = {pretty(sol[y])}"],
                       f"Solving directly, x equals {speak(pretty(sol[x]))} and y equals {speak(pretty(sol[y]))}.", answer=True))
        return S

    vn, un = str(v), str(u)
    S.append(Scene(["Method: Elimination", f"We will eliminate {vn}"], f"We will use the elimination method and eliminate {vn}."))
    m1, m2 = pv2, pv1
    if pv1 == pv2:
        op, e_a, e_b = "subtract", (a1, b1, c1), (a2, b2, c2)
        S.append(Scene([f"The {vn} coefficients are equal, so subtract (2) from (1)"], f"The coefficients of {vn} are equal, so we subtract equation two from equation one."))
        K, M = pu1 - pu2, (c1 - c2)
    elif pv1 == -pv2:
        S.append(Scene([f"The {vn} coefficients are opposite, so add (1) and (2)"], f"The coefficients of {vn} are opposite, so we add the two equations."))
        K, M = pu1 + pu2, (c1 + c2)
    else:
        n1 = _lin(a1 * m1, b1 * m1, c1 * m1)
        n2 = _lin(a2 * m2, b2 * m2, c2 * m2)
        S.append(Scene([f"Multiply (1) by {pretty(m1)} and (2) by {pretty(m2)}:", f"(3)  {n1}", f"(4)  {n2}"],
                       f"To make the coefficients of {vn} equal, multiply equation one by {speak(pretty(m1))} and equation two by {speak(pretty(m2))}."))
        K, M = pu1 * m1 - pu2 * m2, c1 * m1 - c2 * m2
        S.append(Scene(["Subtract (4) from (3):"], "Now subtract equation four from equation three."))
    uval = sp.nsimplify(M / K)
    S.append(Scene([f"⇒ {pretty(K * u)} = {pretty(M)}", f"⇒ {un} = {pretty(uval)}"],
                   f"This gives {speak(pretty(K * u))} equals {speak(pretty(M))}. So {un} equals {speak(pretty(uval))}."))
    vval = sp.nsimplify((c1 - pu1 * uval) / pv1)
    S.append(Scene([f"Put {un} = {pretty(uval)} in (1):", f"⇒ {pretty(pv1 * v)} = {pretty(c1 - pu1 * uval)}", f"⇒ {vn} = {pretty(vval)}"],
                   f"Substitute {un} equals {speak(pretty(uval))} in equation one. We get {vn} equals {speak(pretty(vval))}."))
    xv, yv = (uval, vval) if u == x else (vval, uval)
    S.append(Scene(["Final Answer:", f"x = {pretty(xv)},   y = {pretty(yv)}"],
                   f"Therefore, x equals {speak(pretty(xv))} and y equals {speak(pretty(yv))}.", answer=True))
    ok1 = sp.simplify(a1 * xv + b1 * yv - c1) == 0
    ok2 = sp.simplify(a2 * xv + b2 * yv - c2) == 0
    if ok1 and ok2:
        S.append(Scene(["Check: both equations are satisfied  ✓"], "Putting these values back in both equations, they are both satisfied."))
    return S


# ------------------------------------------------------------------- speed --
_UNIT_WORDS = {"km": "kilometers", "m": "meters", "cm": "centimeters", "h": "hours", "hr": "hours", "s": "seconds",
               "min": "minutes", "mi": "miles"}


def _num(v: float) -> str:
    return f"{v:.2f}".rstrip("0").rstrip(".")


def solve_speed(distance=None, time=None, speed=None, dist_unit="km", time_unit="h") -> List[Scene]:
    du, tu = dist_unit or "km", time_unit or "h"
    dw, tw = _UNIT_WORDS.get(du, du), _UNIT_WORDS.get(tu, tu)
    su = f"{du}/{tu}"
    given = [(n, v) for n, v in (("distance", distance), ("time", time), ("speed", speed)) if v is not None]
    if len(given) != 2:
        raise ProblemError("Give me exactly two of distance, time and speed.")
    lines, voice = ["Given:"], "Given. "
    if distance is not None:
        lines.append(f"Distance = {_num(distance)} {du}"); voice += f"Distance is {_num(distance)} {dw}. "
    if time is not None:
        lines.append(f"Time = {_num(time)} {tu}"); voice += f"Time is {_num(time)} {tw}. "
    if speed is not None:
        lines.append(f"Speed = {_num(speed)} {su}"); voice += f"Speed is {_num(speed)} {dw} per {tw[:-1] if tw.endswith('s') else tw}. "
    S = [Scene(lines, voice)]
    if speed is None:
        if time == 0:
            raise ProblemError("Time cannot be zero.")
        r = distance / time
        S += [Scene(["Formula:", "Speed = Distance / Time"], "We know that speed equals distance divided by time."),
              Scene(["Substituting the values:", f"⇒ Speed = {_num(distance)} / {_num(time)}"], f"Substituting the values, speed equals {_num(distance)} divided by {_num(time)}."),
              Scene([f"⇒ Speed = {_num(r)} {su}"], f"Therefore, the speed is {_num(r)} {dw} per {tw[:-1] if tw.endswith('s') else tw}.", answer=True)]
    elif distance is None:
        r = speed * time
        S += [Scene(["Formula:", "Distance = Speed × Time"], "We know that distance equals speed multiplied by time."),
              Scene(["Substituting the values:", f"⇒ Distance = {_num(speed)} × {_num(time)}"], f"Substituting, distance equals {_num(speed)} times {_num(time)}."),
              Scene([f"⇒ Distance = {_num(r)} {du}"], f"Therefore, the distance is {_num(r)} {dw}.", answer=True)]
    else:
        if speed == 0:
            raise ProblemError("Speed cannot be zero.")
        r = distance / speed
        S += [Scene(["Formula:", "Time = Distance / Speed"], "We know that time equals distance divided by speed."),
              Scene(["Substituting the values:", f"⇒ Time = {_num(distance)} / {_num(speed)}"], f"Substituting, time equals {_num(distance)} divided by {_num(speed)}."),
              Scene([f"⇒ Time = {_num(r)} {tu}"], f"Therefore, the time taken is {_num(r)} {tw}.", answer=True)]
    return S


# ---------------------------------------------------------------- dispatch --
def solve_equation_text(text: str) -> List[Scene]:
    eqs = parse_equations(text)
    if len(eqs) == 2:
        return solve_system(eqs[0], eqs[1])
    lhs, rhs = eqs[0]
    free = (lhs - rhs).free_symbols
    if free - {x}:
        if free <= {x, y} and y in free:
            raise ProblemError("This equation has both x and y. Please give two equations to solve together.")
        raise ProblemError("Please use x as the unknown.")
    if x not in free:
        raise ProblemError("There is no x in this equation.")
    deg = sp.Poly(sp.expand(lhs - rhs), x).degree() if sp.expand(lhs - rhs).is_polynomial(x) else None
    if deg is None:
        raise ProblemError("I can solve polynomial equations for now (no x in denominators or inside functions).")
    if deg == 1:
        return solve_linear(lhs, rhs)
    if deg == 2:
        return solve_quadratic(lhs, rhs)
    return solve_polynomial(lhs, rhs)
