"""Recompute every auto-marked answer in add_finance_questions with SymPy.

Each answer is worked out here from the question alone, independently of the
text in the command, and compared with what the command stores. Run:

    .venv/bin/python scripts/check_finance_answers.py
"""
import os
import sys

import django
import sympy as sp

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "lcstats.settings")
django.setup()

from interactive_lessons.management.commands.add_finance_questions import NEW_QUESTIONS  # noqa: E402

Q = sp.Rational


def money(v):
    return round(float(v), 2)


def pct(v, places=2):
    return round(float(100 * v), places)


i = Q(6, 100)
amort = 20000 * i * (1 + i) ** 5 / ((1 + i) ** 5 - 1)
dep_rate = 1 - Q(1, 6) ** Q(1, 5)
doubling = sp.log(2) / sp.log(Q(106, 100))

EXPECTED = {
    ("PV_SINGLE", "(a)"): money(5000 / Q(103, 100) ** 4),
    ("PV_COMPARE", "(a)"): money(11500 / Q(105, 100) ** 3),
    ("PV_COMPARE", "(b)"): "A" if 11500 / Q(105, 100) ** 3 < 10000 else "B",
    ("PV_STREAM", "(a)"): money(2000 / Q(104, 100)),
    ("PV_STREAM", "(b)"): money(sum(2000 / Q(104, 100) ** k for k in (1, 2, 3))),
    ("PV_RATE", "(a)"): pct(Q(10000, 8000) ** Q(1, 5) - 1),
    ("AER_FROM_MONTHLY", "(a)"): pct(Q(1005, 1000) ** 12 - 1),
    ("MONTHLY_FROM_AER", "(a)"): pct(Q(105, 100) ** Q(1, 12) - 1, 3),
    ("DOUBLING", "(a)"): int(sp.ceiling(doubling)),
    ("AMORTISATION", "(a)"): money(amort),
    # The total interest a student can work out from repayments rounded to
    # the cent: 5 x 4747.93 - 20000 (the unrounded total is 3739.64).
    ("AMORTISATION", "(b)"): money(5 * money(amort) - 20000),
    ("DEP_VALUE", "(a)"): money(30000 * Q(85, 100) ** 4),
    ("DEP_RATE", "(a)"): pct(1 - Q(20000, 50000) ** Q(1, 6)),
    ("DEP_COMPARE", "(a)"): money(Q(12000 - 2000, 5)),
    ("DEP_COMPARE", "(b)"): pct(dep_rate),
    ("DEP_COMPARE", "(c)"): money(12000 * (1 - dep_rate) ** 2),
    ("SAVINGS_SERIES", "(a)"): money(200 * Q(1004, 1000) ** 12),
    ("SAVINGS_SERIES", "(b)"): money(sum(200 * Q(1004, 1000) ** k for k in range(1, 13))),
    ("LOAN_SERIES", "(a)"): "C",
    ("LOAN_SERIES", "(b)"): money(sp.nsolve(
        sp.Symbol("A") * sum(1 / Q(1005, 1000) ** k for k in range(1, 25)) - 10000,
        sp.Symbol("A"), 400)),
    ("PERPETUITY", "(a)"): round(float(1 / Q(105, 100)), 3),
    ("PERPETUITY", "(b)"): money(sp.limit(
        sp.summation(1000 / Q(105, 100) ** sp.Symbol("k"), (sp.Symbol("k"), 1, sp.Symbol("n"))),
        sp.Symbol("n"), sp.oo)),
}

# Facts quoted in the worked solutions.
assert money(10000 * Q(105, 100) ** 3) == 11576.25
assert round(float(Q(106, 100) ** 11), 3) == 1.898 and round(float(Q(106, 100) ** 12), 3) == 2.012
assert 11 < doubling < 12
assert money(5 * money(amort)) == 23739.65
assert 12000 - 2 * 2000 == 8000
assert [money(2000 / Q(104, 100) ** k) for k in (1, 2, 3)] == [1923.08, 1849.11, 1777.99]
assert Q(5, 100) * 20000 == 1000

failures = checked = 0
for name, entry in NEW_QUESTIONS.items():
    for p in entry["parts"]:
        key = (name, p["label"])
        want = EXPECTED.get(key)
        got = p["answer"]
        checked += 1
        ok = got == want if isinstance(want, str) else abs(float(got) - float(want)) < 0.005
        failures += not ok
        print(f"{'ok  ' if ok else 'FAIL'} {name} {p['label']}: stored {got!r}  computed {want}")

missing = {(n, p["label"]) for n, e in NEW_QUESTIONS.items() for p in e["parts"]} - set(EXPECTED)
print(f"\n{checked} answers checked, {failures} failures, {len(missing)} without a check")
sys.exit(1 if failures or missing else 0)
