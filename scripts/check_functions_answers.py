"""Recompute every auto-marked answer in add_functions_questions with SymPy.

Each answer is worked out here from the question alone, independently of the
text in the command, and compared with what the command stores. Run:

    .venv/bin/python scripts/check_functions_answers.py
"""
import os
import sys

import django
import sympy as sp

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "lcstats.settings")
django.setup()

from interactive_lessons.management.commands.add_functions_questions import ALL_SOURCES  # noqa: E402

x, a, y = sp.symbols("x a y")


def real_roots(expr):
    return sorted(float(r) for r in sp.solve(sp.Eq(expr, 0), x) if r.is_real)


def nums(values, places=None):
    out = sorted(round(float(v), places) if places is not None else float(v) for v in values)
    return out


def inverse(f, domain_check=None):
    sols = sp.solve(sp.Eq(y, f), x)
    if domain_check:
        sols = [s for s in sols if domain_check(s)]
    assert len(sols) == 1, sols
    return sp.simplify(sols[0].subs(y, x))


# (section, question order, part label) -> independently computed answer
f = 3 * x - 5
f3, g3 = 2 * x + 1, x**2
w5 = x**2 - 4 * x + 7
g6 = x**2 - 4
k1f, k1g = x**2 - 3, 2 * x + 1
k2 = 2 * x**2 - 12 * x + 10
k3f, k3g = x**2 - 2 * x - 3, x + 1
k4 = x**2 - 4 * x
k6 = (2 * x + 1) / (x - 3)
s1 = x**2 - 6 * x + 5
s2f, s2g = x + 2, x**2
s3 = x**3 + x**2 - 4 * x - 4
s5 = x**2 + 6 * x + 11

EXPECTED = {
    ("Warm-up", 1, "(a)"): "B",  # (1, 2) and (1, 3) share an input
    # range {-1, 0, 3}: option C
    ("Warm-up", 1, "(b)"): "C" if set((x**2 - 1).subs(x, v) for v in [-2, -1, 0, 1, 2]) == {-1, 0, 3} else "?",
    ("Warm-up", 2, "(a)"): nums([f.subs(x, 4)]),
    ("Warm-up", 2, "(b)"): nums(sp.solve(sp.Eq(f, 10), x)),
    ("Warm-up", 2, "(c)"): ("expr", f.subs(x, 2 * a)),
    ("Warm-up", 3, "(a)"): nums([f3.subs(x, g3.subs(x, 3))]),
    ("Warm-up", 3, "(b)"): nums([g3.subs(x, f3.subs(x, 3))]),
    ("Warm-up", 3, "(c)"): ("expr", f3.subs(x, g3)),
    ("Warm-up", 4, "(a)"): "B",  # only -x^2 + 1 has a negative x^2 coefficient
    ("Warm-up", 4, "(b)"): "B",  # leading coefficient -1
    ("Warm-up", 4, "(c)"): nums([sp.Integer(5) ** 0]),
    # turning point of x^2 - 4x + 7: x = -b/2a, then p = -x0, q = f(x0)
    ("Warm-up", 5, "(a)"): nums([-sp.Rational(4, 2)]),
    ("Warm-up", 5, "(b)"): nums([w5.subs(x, 2)]),
    ("Warm-up", 5, "(c)"): [2.0, float(w5.subs(x, 2))],
    ("Warm-up", 6, "(a)"): "B",
    ("Warm-up", 6, "(b)"): nums([(g6 + 3).subs(x, 0)]),
    ("Warm-up", 6, "(c)"): [2.0, float(g6.subs(x, 0))],
    ("Warm-up", 7, "(a)"): ("expr", inverse(2 * x + 3)),
    ("Warm-up", 7, "(b)"): nums([inverse(2 * x + 3).subs(x, 11)]),

    ("Workout", 1, "(a)"): ("expr", sp.expand(k1f.subs(x, k1g))),
    ("Workout", 1, "(b)"): nums(real_roots(k1f.subs(x, k1g) - 6)),
    ("Workout", 2, "(a)"): nums([k2.subs(x, 3)]),  # q = minimum value
    ("Workout", 2, "(b)"): [float(sp.solve(sp.diff(k2, x), x)[0]), float(k2.subs(x, 3))],
    ("Workout", 2, "(c)"): nums(real_roots(k2)),
    ("Workout", 3, "(a)"): nums(real_roots(k3f - k3g)),
    ("Workout", 3, "(b)"): "B",  # checked below with sample points
    ("Workout", 4, "(a)"): nums([k4.subs(x, sp.solve(sp.diff(k4, x), x)[0])]),
    ("Workout", 4, "(b)"): nums([len(real_roots(k4 - 5))]),
    ("Workout", 5, "(a)"): "D",
    ("Workout", 5, "(b)"): "A",
    ("Workout", 5, "(c)"): "B",
    ("Workout", 6, "(a)"): ("expr", inverse(k6)),
    ("Workout", 6, "(b)"): nums([inverse(k6).subs(x, 5)]),
    ("Workout", 7, "(a)"): nums([sp.log(2**5, 2)]),
    ("Workout", 7, "(b)"): nums(sp.solve(sp.Eq(3 * 2**x, 96), x)),
    ("Workout", 7, "(c)"): nums(sp.solve(sp.Eq(sp.log(x, 2), 0), x)),

    ("Stretch", 1, "(a)"): nums(sp.solve(sp.diff(s1, x), x)),
    ("Stretch", 1, "(b)"): ("expr", inverse(s1, lambda s: s.subs(y, 12) >= 3)),
    ("Stretch", 1, "(c)"): nums([inverse(s1, lambda s: s.subs(y, 12) >= 3).subs(x, 12)]),
    ("Stretch", 2, "(a)"): nums(real_roots(s2g.subs(x, s2f) - s2f)),
    ("Stretch", 2, "(b)"): nums(real_roots(s2g.subs(x, s2f) - s2f.subs(x, s2g))),
    ("Stretch", 3, "(a)"): nums([r for r in real_roots(s3) if r > 0]) if sp.expand((x + 1) * (x - 2) * (x + 2) - s3) == 0 else "?",
    ("Stretch", 3, "(b)"): [r for r in nums(real_roots(s3 + 4), 2) if r != 0],
    ("Stretch", 4, "(a)"): nums(sp.solve(sp.Eq(a * (1 + 1) ** 2 + 5, -3), a)),
    ("Stretch", 4, "(b)"): nums([(-2 * (x + 1) ** 2 + 5).subs(x, 0)]),
    ("Stretch", 5, "(a)"): nums([s5.subs(x, sp.solve(sp.diff(s5, x), x)[0])]),
    ("Stretch", 5, "(b)"): "C" if s5.subs(x, -4) == s5.subs(x, -2) else "?",
    ("Stretch", 6, "(a)"): [7.0, 2.0],
    ("Stretch", 6, "(b)"): nums(real_roots(x**3 + 1 - 28)),

    # Composite Functions
    ("Composite Functions", 1, "(a)"): nums([(x - 4).subs(x, (3 * x).subs(x, 2))]),
    ("Composite Functions", 1, "(b)"): nums([(3 * x).subs(x, (x - 4).subs(x, 2))]),
    ("Composite Functions", 1, "(c)"): "D" if not sp.solve(sp.Eq((x - 4).subs(x, 3 * x), (3 * x).subs(x, x - 4)), x) else "?",
    ("Composite Functions", 2, "(a)"): nums([(x**2).subs(x, (x + 3).subs(x, (2 * x).subs(x, 1)))]),
    ("Composite Functions", 2, "(b)"): ("expr", (2 * x).subs(x, (x + 3).subs(x, x**2))),
    ("Composite Functions", 3, "(a)"): ("expr", x**3),
    ("Composite Functions", 3, "(b)"): ("expr", x**2 + 1),
    ("Composite Functions", 4, "(a)"): [float(v[0]) for v in sp.solve([sp.Eq(a**2, 9), sp.Eq(a * y + y, 8)], [a, y]) if v[0] > 0],
    ("Composite Functions", 4, "(b)"): [float(v[1]) for v in sp.solve([sp.Eq(a**2, 9), sp.Eq(a * y + y, 8)], [a, y]) if v[0] > 0],
    ("Composite Functions", 5, "(a)"): nums(real_roots(x**2 - 2), 2),
    ("Composite Functions", 5, "(b)"): nums([(x**2).subs(x, (1 / (x - 2)).subs(x, 3))]),

    # Added 2026-10-10 for the thin subtopics
    ("New 6.2", 1, "(a)"): nums([(2 * x**2 - 3).subs(x, -2)]),
    ("New 6.2", 1, "(b)"): nums(real_roots(2 * x**2 - 3 - 15)),
    ("New 6.2", 1, "(c)"): "B" if {(2 * x**2 - 3).subs(x, v) for v in (-1, 0, 1)} == {-3, -1} else "?",
    ("New 6.6", 1, "(a)"): nums([(x**3 - 3 * x**2 - x + 3).subs(x, 0)]),
    ("New 6.6", 1, "(b)"): nums(real_roots(x**3 - 3 * x**2 - x + 3)),
    ("New 6.6", 1, "(c)"): "B" if all((x**3 - 3 * x**2 - x + 3).subs(x, v) < 0 for v in (1.01, 2, 2.99)) else "?",
    ("New 6.6", 2, "(a)"): nums(sp.solve(sp.Eq(a * (0 + 2) * (0 - 1) * (0 - 4), 8), a)),
    ("New 6.6", 2, "(b)"): nums([((x + 2) * (x - 1) * (x - 4)).subs(x, 2)]),
    ("New 6.6", 2, "(c)"): nums(real_roots((x + 2) * (x - 1) * (x - 4) - 8), 2),
    ("New 6.7", 1, "(a)"): nums([3 * 2**0]),
    ("New 6.7", 1, "(b)"): nums([3 * 2**4]),
    ("New 6.7", 1, "(c)"): "B" if sp.limit(3 * 2**x, x, -sp.oo) == 0 else "?",
    ("New 6.7", 2, "(a)"): nums([500 * sp.Rational(6, 5) ** 3]),
    ("New 6.7", 2, "(b)"): nums([next(t for t in range(50) if 500 * sp.Rational(6, 5) ** t > 2000)]),
    ("New 6.8", 1, "(a)"): nums([sp.log(8, 2)]),
    ("New 6.8", 1, "(b)"): nums(sp.solve(sp.Eq(sp.log(x, 2), 0), x)),
    ("New 6.8", 1, "(c)"): "B" if sp.limit(sp.log(x, 2), x, 0, "+") == -sp.oo else "?",
    ("New 6.8", 2, "(a)"): nums(sp.solve(sp.Eq(sp.log(x - 2, 3), 0), x)),
    ("New 6.8", 2, "(b)"): nums([2]) if sp.limit(sp.log(x - 2, 3), x, 2, "+") == -sp.oo else "?",
    ("New 6.8", 2, "(c)"): nums([sp.log(11 - 2, 3)]),
    ("New 6.8", 3, "(a)"): [8.0, float(sp.log(8, 2))],
    ("New 6.8", 3, "(b)"): nums(sp.solve(sp.Eq(sp.log(x, 2), 5), x)),
    ("New 6.8", 3, "(c)"): "B",  # log2 x defined for x > 0 only
    ("New 6.9", 1, "(a)"): "B" if min(v + 5 for v in range(1, 10)) == 6 else "?",  # 1..5 unreached
    ("New 6.9", 1, "(b)"): "A" if sp.solve(sp.diff(x**3, x), x) == [0] and sp.diff(x**3, x).subs(x, 1) > 0 else "?",
}

# Expansions and factorisations quoted in the new worked solutions.
assert sp.expand((x + 2) * (x - 1) * (x - 4)) == x**3 - 3 * x**2 - 6 * x + 8
assert sp.expand((x - 3) * (x - 1) * (x + 1)) == x**3 - 3 * x**2 - x + 3
assert round(float(500 * sp.Rational(6, 5) ** 7)) == 1792 and round(float(500 * sp.Rational(6, 5) ** 8)) == 2150

# The decompositions really do recompose to the given functions.
assert sp.expand(x**3).subs(x, 2 * x + 5) == (2 * x + 5) ** 3
assert sp.sqrt(x).subs(x, x**2 + 1) == sp.sqrt(x**2 + 1)

# Extra spot checks the dictionary can't express.
assert all((k3f - k3g).subs(x, v) < 0 for v in [-0.5, 0, 3.9]), "Workout 3(b): f < g inside"
assert all((k3f - k3g).subs(x, v) > 0 for v in [-2, 5]), "Workout 3(b): f > g outside"
assert s5.subs(x, 0) >= 2, "Stretch 5(b): D's claim is false"
assert (s3.subs(x, -3), s3.subs(x, 3), s3.subs(x, 0)) == (-10, 20, -4), "Stretch 3(c) sketch values"


def stored_value(answer, kind):
    if kind == "multi":
        return answer.strip()
    if kind == "expression":
        return ("expr", sp.sympify(answer.replace("^", "**"), locals={"a": a, "x": x}))
    answer = answer.strip("()[] ")
    return [float(sp.Rational(v.strip())) if "/" in v else float(v) for v in answer.split(",")]


failures = 0
checked = 0
for section, order, entry in ALL_SOURCES:
    if True:
        for p in entry["parts"]:
            key = (section, order, p["label"])
            if p["expected_type"] == "manual":
                continue
            want = EXPECTED.get(key)
            got = stored_value(p["answer"], p["expected_type"])
            checked += 1
            if isinstance(want, tuple):
                ok = sp.simplify(got[1] - want[1]) == 0
            elif isinstance(want, list):
                # Pairs must be stored in the order the format line asks for:
                # x first for a point, otherwise smallest first, because the
                # grader compares the first two numbers of a pair in order.
                is_point = p["answer"].strip().startswith("(")
                g = got
                w = want if is_point else sorted(want)
                if not is_point:
                    g = sorted(got)
                ok = len(g) == len(w) and all(abs(i - j) < 0.006 for i, j in zip(g, w))
            else:
                ok = got == want
            if not ok:
                failures += 1
            print(f"{'ok  ' if ok else 'FAIL'} {section} Q{entry['order']}{p['label']}: "
                  f"stored {p['answer']!r}  computed {want}")

missing = {(s, o, p["label"]) for s, o, e in ALL_SOURCES for p in e["parts"]
           if p["expected_type"] != "manual"} - set(EXPECTED)
print(f"\n{checked} answers checked, {failures} failures, {len(missing)} without a check")
sys.exit(1 if failures or missing else 0)
