"""Check every Proof by Induction answer and multiple-choice option with SymPy.

The numeric answers are recomputed from the statements. For each
multiple-choice part, every option is tested: the stored answer must be the
only option that is both true and does the job, and the solutions' remarks
about the wrong options must be right. Run:

    .venv/bin/python scripts/check_induction_answers.py
"""
import os
import sys

import django
import sympy as sp

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "lcstats.settings")
django.setup()

from interactive_lessons.management.commands.add_induction_questions import QUESTIONS  # noqa: E402

k = sp.Symbol("k", positive=True, integer=True)
R = sp.Rational
failures = []


def check(name, ok):
    print(f"{'ok  ' if ok else 'FAIL'} {name}")
    if not ok:
        failures.append(name)


def same(a, b):
    return sp.simplify(sp.expand(a - b)) == 0


def holds(ineq, start, stop=60):
    """True if the inequality in k holds for every k from start to stop."""
    return all(bool(ineq.subs(k, v)) for v in range(start, stop))


stored = {(s, q["order"], p["label"]): p["answer"]
          for s, _, qs in QUESTIONS for q in qs for p in q["parts"]}

# ---- Divisibility ---------------------------------------------------------
P1 = lambda n: 7**n - 3**n  # noqa: E731
check("Div 1 (a)", stored[("Divisibility", 1, "(a)")] == str(P1(1)) and P1(1) % 4 == 0)
target = 7**(k + 1) - 3**(k + 1)
opts = {
    "A": 8 * 7**k - 7**k - 3**(k + 1),
    "B": 5 * 7**k + 2 * 7**k - 3**(k + 1),
    "C": 4 * 7**k + 3 * (7**k - 3**k),
    "D": 7**(k + 1) - 7**k * 7 + 7**k * 4,
}
# A and B are true rewrites but leave no P(k); only C shows 4 | P(k+1).
check("Div 1 (b) C equals P(k+1) and is 4*7^k + 3P(k)",
      same(opts["C"], target) and same(opts["C"] - 3 * P1(k), 4 * 7**k))
check("Div 1 (b) D is not P(k+1)", not same(opts["D"], target))
check("Div 1 (b) stored C", stored[("Divisibility", 1, "(b)")] == "C")

P2 = lambda n: n**3 + 2 * n  # noqa: E731
check("Div 2 (a)", stored[("Divisibility", 2, "(a)")] == str(P2(1)))
target = sp.expand(P2(k + 1))
check("Div 2 (b) expansion in the prompt", same(target, k**3 + 3 * k**2 + 5 * k + 3))
opts = {
    "A": P2(k) + 3 * k**2 + 3 * k,
    "B": P2(k) + 3 * (k**2 + k + 1),
    "C": P2(k) + (3 * k**2 + 5 * k + 3),
    "D": 3 * P2(k) + (k**2 + k + 1),
}
check("Div 2 (b) only B is right", same(opts["B"], target) and same(target - opts["A"], 3)
      and not same(opts["C"], target) and not same(opts["D"], target))
check("Div 2 (b) stored B", stored[("Divisibility", 2, "(b)")] == "B")

P3 = lambda n: 4**n + 6 * n - 1  # noqa: E731
check("Div 3 (a)", stored[("Divisibility", 3, "(a)")] == str(P3(1)))
target = P3(k + 1)
opts = {
    "A": 4 * P3(k) - 9 * (2 * k + 1),
    "B": 4 * P3(k) + 9 * (2 * k - 1),
    "C": 9 * P3(k) - 4 * (2 * k - 1),
    "D": 4 * P3(k) - 9 * (2 * k - 1),
}
check("Div 3 (b) only D equals P(k+1)",
      [L for L, e in opts.items() if same(e, target)] == ["D"])
check("Div 3 (b) stored D", stored[("Divisibility", 3, "(b)")] == "D")

# ---- Series ---------------------------------------------------------------
n = sp.Symbol("n", positive=True, integer=True)
r = sp.Symbol("r", positive=True, integer=True)

rhs = n * (3 * n - 1) / 2
check("Series 1 formula", same(sp.summation(3 * r - 2, (r, 1, n)), rhs))
check("Series 1 (a)", stored[("Series", 1, "(a)")] == str(rhs.subs(n, 1)))
term = (3 * n - 2).subs(n, k + 1)
opts = {"A": 3 * k + 1, "B": 3 * k - 2, "C": 3 * k + 4, "D": 3 * k - 1}
check("Series 1 (b) only A is the (k+1)th term",
      [L for L, e in opts.items() if same(e, term)] == ["A"] and same(opts["B"], 3 * k - 2))
check("Series 1 (b) stored A", stored[("Series", 1, "(b)")] == "A")
check("Series 1 (c) step", same(rhs.subs(n, k) + term, rhs.subs(n, k + 1))
      and same(rhs.subs(n, k + 1), (k + 1) * (3 * k + 2) / 2))

rhs = n * (n + 1) * (2 * n + 1) / 6
check("Series 2 formula", same(sp.summation(r**2, (r, 1, n)), rhs))
check("Series 2 (a)", stored[("Series", 2, "(a)")] == str(rhs.subs(n, 1)))
target = rhs.subs(n, k) + (k + 1)**2
opts = {
    "A": (k + 1) / 6 * (k * (2 * k + 1) + 6),
    "B": (k + 1) / 6 * (k * (2 * k + 1) + (k + 1)),
    "C": k / 6 * ((k + 1) * (2 * k + 1) + 6 * (k + 1)),
    "D": (k + 1) / 6 * (k * (2 * k + 1) + 6 * (k + 1)),
}
check("Series 2 (b) only D is right",
      [L for L, e in opts.items() if same(e, target)] == ["D"])
check("Series 2 (b) B is (k+1)^2 not multiplied by 6",
      same(opts["B"], rhs.subs(n, k) + (k + 1)**2 / 6))
check("Series 2 (b) stored D", stored[("Series", 2, "(b)")] == "D")
check("Series 2 (c) step", same(target, (k + 1) * (k + 2) * (2 * k + 3) / 6)
      and same(sp.expand(2 * k**2 + 7 * k + 6), sp.expand((k + 2) * (2 * k + 3))))

rhs = n / (n + 1)
check("Series 3 formula", same(sp.summation(1 / (r * (r + 1)), (r, 1, n)), rhs))
check("Series 3 (a)", stored[("Series", 3, "(a)")] == str(rhs.subs(n, 1)))
target = k / (k + 1) + 1 / ((k + 1) * (k + 2))
opts = {"A": k / (k + 2), "B": (k + 1) / (k + 2),
        "C": (k**2 + 1) / ((k + 1) * (k + 2)), "D": 1 / (k + 2)}
check("Series 3 (b) only B is right",
      [L for L, e in opts.items() if same(e, target)] == ["B"])
check("Series 3 (b) stored B", stored[("Series", 3, "(b)")] == "B")

# ---- Inequalities ---------------------------------------------------------
check("Ineq 1 (a) 2^4 = 4^2 = 16", 2**4 == 4**2 == int(stored[("Inequalities", 1, "(a)")]))
check("Ineq 1 holds from n = 5 on and fails at n = 4",
      all(2**m > m**2 for m in range(5, 60)) and not 2**4 > 4**2)
opts = {
    "A": k**2 > (k + 1)**2,
    "B": 2 * k**2 > 2 * (k + 1)**2,
    "C": 2 * k**2 >= (k + 1)**2,
    "D": 2 * k**2 >= k**2 + 1,
}
check("Ineq 1 (b) A and B false for every k", not any(
    bool(opts[L].subs(k, v)) for L in "AB" for v in range(1, 60)))
check("Ineq 1 (b) C holds for k >= 5", holds(opts["C"], 5))
check("Ineq 1 (b) D holds but falls short of (k+1)^2",
      holds(opts["D"], 5) and holds(k**2 + 1 < (k + 1)**2, 1))
check("Ineq 1 (b) stored C", stored[("Inequalities", 1, "(b)")] == "C")
check("Ineq 1 (c) k(k-2)-1 at k = 5 is 14", (k * (k - 2) - 1).subs(k, 5) == 14)

check("Ineq 2 (a)", stored[("Inequalities", 2, "(a)")] == "3" and 3**1 >= 1 + 2)
opts = {
    "A": 6 * k + 3 >= 2 * k + 3,
    "B": 6 * k + 3 >= 6 * k + 5,
    "C": 6 * k + 3 <= 2 * k + 3,
    "D": 3 * k + 1 >= 2 * k + 3,
}
check("Ineq 2 (b) A holds for every k, B and C never do, D fails at k = 1",
      holds(opts["A"], 1) and not any(bool(opts[L].subs(k, v)) for L in "BC"
                                      for v in range(1, 60))
      and not bool(opts["D"].subs(k, 1)))
check("Ineq 2 (b) stored A", stored[("Inequalities", 2, "(b)")] == "A")

check("Ineq 3 (a) 4! - 2^4", int(stored[("Inequalities", 3, "(a)")])
      == sp.factorial(4) - 2**4 and sp.factorial(3) < 2**3)
t = (k + 1) * 2**k
opts = {
    "A": t >= 2**k,
    "B": t >= 2**(k + 1) * (k + 1),
    "C": t <= 2**(k + 1),
    "D": t >= 2 * 2**k,
}
check("Ineq 3 (b) D holds for k >= 4; A holds but only reaches 2^k",
      holds(opts["D"], 4) and holds(opts["A"], 4))
check("Ineq 3 (b) B never holds, C only for k <= 1",
      not any(bool(opts["B"].subs(k, v)) for v in range(1, 60))
      and [v for v in range(1, 60) if bool(opts["C"].subs(k, v))] == [1])
check("Ineq 3 (b) stored D", stored[("Inequalities", 3, "(b)")] == "D")

print(f"\n{len(failures)} failures")
sys.exit(1 if failures else 0)
