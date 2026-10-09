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

from interactive_lessons.management.commands.add_functions_questions import QUESTIONS  # noqa: E402

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
}

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
    return [float(sp.Rational(v.strip())) if "/" in v else float(v) for v in answer.split(",")]


failures = 0
checked = 0
for section, _, entries in QUESTIONS:
    for entry in entries:
        for p in entry["parts"]:
            key = (section, entry["order"], p["label"])
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
                is_point = "x first" in p["expected_format"]
                g = got
                w = want if is_point else sorted(want)
                if not is_point and got != sorted(got):
                    print(f"     ^ stored out of order: {p['answer']!r}")
                ok = len(g) == len(w) and all(abs(i - j) < 0.006 for i, j in zip(g, w))
            else:
                ok = got == want
            if not ok:
                failures += 1
            print(f"{'ok  ' if ok else 'FAIL'} {section} Q{entry['order']}{p['label']}: "
                  f"stored {p['answer']!r}  computed {want}")

missing = {(s, e["order"], p["label"]) for s, _, es in QUESTIONS for e in es for p in e["parts"]
           if p["expected_type"] != "manual"} - set(EXPECTED)
print(f"\n{checked} answers checked, {failures} failures, {len(missing)} without a check")
sys.exit(1 if failures or missing else 0)
