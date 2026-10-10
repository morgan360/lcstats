"""Add the Finance practice questions, one section per subtopic.

Content authored on local and replayed here so production gets exactly what was
tested. Idempotent, and keyed on content rather than primary key, because ids
differ between local and production. Re-running updates in place and never
duplicates.

Sections follow Active Maths, Chapter 10 (Financial Mathematics): 10.1 present
value, 10.2 compound interest, 10.3 depreciation, 10.4 geometric series. Each
runs from easiest to hardest. The new questions are our own words and numbers.

Every formula used is printed in the Formulae & Tables booklet (pp. 22, 30-31):
compound interest, present value, both depreciation methods, amortisation and
the geometric series sums. So the questions test choosing and using them --
period rates, AER, solving for t or i with logs, and building savings and loan
sums as geometric series -- not recalling them.

The three questions Finance already had (simple interest, compound interest and
the 2013 exam question) all have student attempts. They are *moved* into the
new sections, matched by their first prompt, never re-created or rewritten,
except that their stored answers "€944 or $944$" and "Answer: €2492.36" become
plain numbers the grader can read. Their old sections are deleted once empty.

Money answers are stored as plain numbers to the cent. The grader ignores a
euro sign and reads "2,492.36" as one number when one number is stored.
Every answer was checked with SymPy (scripts/check_finance_answers.py).
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Subject
from interactive_lessons.models import Topic, Question, QuestionPart, Section

TOPIC_NAME = "Finance"
SUBJECT_NAME = "Maths"

EURO = "Amount in euro, to the nearest cent (e.g., 1234.56)"
PCT = "A percentage to 2 decimal places, without the % sign (e.g., 3.25)"
PCT3 = "A percentage to 3 decimal places, without the % sign (e.g., 0.125)"
YEARS = "A whole number of years (e.g., 5)"
NUM = "Number only (e.g., 7 or 0.25)"
LETTER = "Single letter (e.g., B or D)"


def part(label, order, prompt, answer, expected_type, expected_format, max_marks,
         solution):
    return {
        "label": label, "order": order, "prompt": prompt, "answer": answer,
        "expected_format": expected_format, "expected_type": expected_type,
        "max_marks": max_marks, "unlock": 2, "scale": None,
        "solution": solution, "qk": False,
    }


def question(hint, parts):
    return {
        "hint": hint, "solution": None, "is_copyrighted": True,
        "is_exam_question": False, "is_quickkick_suitable": False, "parts": parts,
    }


def existing(prompt_contains, answer_fixes=None):
    """A question Finance already has: moved into place, never rewritten."""
    return {"existing": prompt_contains, "answer_fixes": answer_fixes or {}}


# ---------------------------------------------------------------------------
# 10.1 Present Value
# ---------------------------------------------------------------------------
PV_SINGLE = question(r"""Present value answers "how much would I need to invest **now** to have $F$ later?" From the tables: $P = \dfrac{F}{(1 + i)^t}$, with $i$ as a decimal.""", [
    part("(a)", 0, r"""Ciara needs €5,000 in 4 years' time. How much must she invest now at 3% per annum, compounded annually?""",
         "4442.44", "numeric", EURO, 10,
         r"""$$P = \frac{F}{(1 + i)^t} = \frac{5000}{(1.03)^4} = \frac{5000}{1.12550881} = 4442.44$$

**Answer:** €4,442.44"""),
])

PV_COMPARE = question(r"""To compare money at different times, bring it all to the **same** time. Find the present value of the later amount and compare it with the amount offered now.""", [
    part("(a)", 0, r"""Tomás is offered €10,000 now, or €11,500 in 3 years' time. Money can be invested at 5% per annum, compounded annually.

Find the present value of €11,500 in 3 years' time.""",
         "9934.13", "numeric", EURO, 10,
         r"""$$P = \frac{11500}{(1.05)^3} = \frac{11500}{1.157625} = 9934.13$$

**Answer:** €9,934.13"""),
    part("(b)", 1, r"""Which offer is worth more?

**(A)** €10,000 now

**(B)** €11,500 in 3 years

**(C)** They are worth exactly the same

**(D)** It cannot be decided without knowing inflation

Type the letter of your answer.""",
         "A", "multi", LETTER, 5,
         r"""In today's money the later offer is worth €9,934.13, which is less than €10,000. Invested at 5%, the €10,000 would grow to $10000(1.05)^3 = €11,576.25$, more than €11,500.

**Answer:** A"""),
])

PV_STREAM = question(r"""The present value of several payments is the **sum** of their separate present values. A payment in year $k$ is divided by $(1 + i)^k$.""", [
    part("(a)", 0, r"""A prize pays €2,000 at the end of each of the next 3 years. Using an interest rate of 4% per annum, find the present value of the **first** payment.""",
         "1923.08", "numeric", EURO, 5,
         r"""$$\frac{2000}{1.04} = 1923.08$$

**Answer:** €1,923.08"""),
    part("(b)", 1, r"""Find the present value of all three payments.""",
         "5550.18", "numeric", EURO, 10,
         r"""$$\frac{2000}{1.04} + \frac{2000}{1.04^2} + \frac{2000}{1.04^3} = 1923.08 + 1849.11 + 1777.99 = 5550.18$$

**Answer:** €5,550.18"""),
])

PV_RATE = question(r"""When the rate is the unknown, start from $F = P(1 + i)^t$, divide to get $(1 + i)^t$ on its own, then take the $t$-th root.""", [
    part("(a)", 0, r"""An investment of €8,000 is worth €10,000 after 5 years. Find the annual rate of compound interest.""",
         "4.56", "numeric", PCT, 15,
         r"""$$10000 = 8000(1 + i)^5 \;\Rightarrow\; (1 + i)^5 = 1.25 \;\Rightarrow\; 1 + i = 1.25^{1/5} = 1.04564$$

So $i = 0.04564$, i.e. $4.56\%$.

**Answer:** $4.56\%$"""),
])

# ---------------------------------------------------------------------------
# 10.2 Compound Interest: Loans and Investments
# ---------------------------------------------------------------------------
AER_FROM_MONTHLY = question(r"""The **AER** is the rate that gives the same growth in one year. A monthly rate $i$ compounds 12 times: $\text{AER} = (1 + i)^{12} - 1$.""", [
    part("(a)", 0, r"""A savings account pays 0.5% interest per month. Find the AER.""",
         "6.17", "numeric", PCT, 10,
         r"""$$\text{AER} = (1.005)^{12} - 1 = 1.06168 - 1 = 0.06168$$

**Answer:** $6.17\%$ (not $12 \times 0.5\% = 6\%$: the interest earns interest)"""),
])

MONTHLY_FROM_AER = question(r"""Work backwards from the AER: if $(1 + i)^{12} = 1 + \text{AER}$, then $i = (1 + \text{AER})^{1/12} - 1$.""", [
    part("(a)", 0, r"""An account has an AER of 5%. Find the equivalent monthly interest rate.""",
         "0.407", "numeric", PCT3, 10,
         r"""$$i = (1.05)^{1/12} - 1 = 1.004074 - 1 = 0.004074$$

**Answer:** $0.407\%$ per month"""),
])

DOUBLING = question(r"""Set up $2P = P(1.06)^t$, so $1.06^t = 2$. Take logs of both sides: $t \log 1.06 = \log 2$. Interest is only added at the end of each year, so round **up**.""", [
    part("(a)", 0, r"""Money is invested at 6% per annum, compounded annually. After how many whole years will it first have doubled?""",
         "12", "numeric", YEARS, 15,
         r"""$$1.06^t = 2 \;\Rightarrow\; t = \frac{\ln 2}{\ln 1.06} = 11.9$$

After 11 years it has not yet doubled ($1.06^{11} = 1.898$); after 12 it has ($1.06^{12} = 2.012$).

**Answer:** $12$ years"""),
])

AMORTISATION = question(r"""Equal repayments on a loan: the tables give $A = P\,\dfrac{i(1 + i)^t}{(1 + i)^t - 1}$. The total interest is everything repaid minus what was borrowed.""", [
    part("(a)", 0, r"""Seán borrows €20,000 at 6% per annum, compounded annually. He repays it in 5 equal annual repayments, the first one year after the loan. Find each repayment.""",
         "4747.93", "numeric", EURO, 15,
         r"""$$A = 20000 \times \frac{0.06(1.06)^5}{(1.06)^5 - 1} = 20000 \times \frac{0.080294}{0.338226} = 4747.93$$

**Answer:** €4,747.93"""),
    part("(b)", 1, r"""How much interest does Seán pay in total?""",
         "3739.65", "numeric", EURO, 5,
         r"""$$5 \times 4747.93 - 20000 = 23739.65 - 20000 = 3739.65$$

**Answer:** €3,739.65"""),
])

# ---------------------------------------------------------------------------
# 10.3 Depreciation (Reducing-Balance Method)
# ---------------------------------------------------------------------------
DEP_VALUE = question(r"""Reducing balance: each year the value drops by the same **percentage** of what it was worth at the start of that year. From the tables: $F = P(1 - i)^t$.""", [
    part("(a)", 0, r"""A car bought for €30,000 depreciates at 15% per annum on a reducing balance. Find its value after 4 years.""",
         "15660.19", "numeric", EURO, 10,
         r"""$$F = 30000(1 - 0.15)^4 = 30000(0.85)^4 = 30000 \times 0.52200625 = 15660.19$$

**Answer:** €15,660.19"""),
])

DEP_RATE = question(r"""With $F = P(1 - i)^t$ and $i$ unknown: divide to get $(1 - i)^t = \dfrac{F}{P}$, take the $t$-th root, then subtract from 1.""", [
    part("(a)", 0, r"""A machine bought for €50,000 is worth €20,000 after 6 years. Find the annual rate of depreciation, using the reducing-balance method.""",
         "14.16", "numeric", PCT, 15,
         r"""$$(1 - i)^6 = \frac{20000}{50000} = 0.4 \;\Rightarrow\; 1 - i = 0.4^{1/6} = 0.85837$$

So $i = 0.14163$, i.e. $14.16\%$.

**Answer:** $14.16\%$"""),
])

DEP_COMPARE = question(r"""**Straight-line** takes off the same **amount** each year: $A = \dfrac{P - S}{t}$. **Reducing balance** takes off the same **percentage** each year, so it drops fastest at the start.""", [
    part("(a)", 0, r"""Equipment costs €12,000 and will have a scrap value of €2,000 after 5 years. Using the straight-line method, find the annual depreciation.""",
         "2000", "numeric", EURO, 5,
         r"""$$A = \frac{P - S}{t} = \frac{12000 - 2000}{5} = 2000$$

**Answer:** €2,000 per year"""),
    part("(b)", 1, r"""Find the reducing-balance rate that also takes €12,000 to €2,000 in 5 years.""",
         "30.12", "numeric", PCT, 10,
         r"""$$(1 - i)^5 = \frac{2000}{12000} = \frac{1}{6} \;\Rightarrow\; 1 - i = 0.69883 \;\Rightarrow\; i = 0.30117$$

**Answer:** $30.12\%$"""),
    part("(c)", 2, r"""Using that reducing-balance rate, find the value of the equipment after 2 years.""",
         "5860.31", "numeric", EURO, 10,
         r"""$$12000(1 - 0.30117)^2 = 12000 \times 0.48836 = 5860.31$$

Under the straight-line method it would still be worth $12000 - 2 \times 2000 = €8,000$: reducing balance loses value faster early on.

**Answer:** €5,860.31"""),
])

# ---------------------------------------------------------------------------
# 10.4 Applications and Problems Involving Geometric Series
# ---------------------------------------------------------------------------
SAVINGS_SERIES = question(r"""Each deposit grows for a different number of months. List the final value of each one: they form a geometric series, which the tables sum with $S_n = \dfrac{a(1 - r^n)}{1 - r}$.""", [
    part("(a)", 0, r"""Aoife saves €200 at the **start** of each month for 12 months, in an account paying 0.4% per month. What is her **first** deposit worth at the end of the 12 months?""",
         "209.81", "numeric", EURO, 5,
         r"""The first deposit earns interest for all 12 months:

$$200(1.004)^{12} = 209.81$$

**Answer:** €209.81"""),
    part("(b)", 1, r"""How much is in the account at the end of the 12 months?""",
         "2463.32", "numeric", EURO, 15,
         r"""The last deposit earns one month's interest, the first earns twelve:

$$200(1.004) + 200(1.004)^2 + \cdots + 200(1.004)^{12}$$

A geometric series with $a = 200(1.004)$, $r = 1.004$, $n = 12$:

$$S_{12} = \frac{200(1.004)\left(1 - 1.004^{12}\right)}{1 - 1.004} = 2463.32$$

**Answer:** €2,463.32"""),
])

LOAN_SERIES = question(r"""A loan is repaid when the present values of all the repayments add up to the amount borrowed. Repayment $k$ has present value $\dfrac{A}{(1 + i)^k}$: that is a geometric series.""", [
    part("(a)", 0, r"""Dara borrows €10,000 at 0.5% per month and repays it in 24 equal monthly repayments of $A$, the first one month after the loan. Which equation is correct?

**(A)** $10000 = 24A$

**(B)** $10000(1.005)^{24} = 24A$

**(C)** $10000 = \dfrac{A}{1.005} + \dfrac{A}{1.005^2} + \cdots + \dfrac{A}{1.005^{24}}$

**(D)** $10000 = A(1.005) + A(1.005)^2 + \cdots + A(1.005)^{24}$

Type the letter of your answer.""",
         "C", "multi", LETTER, 5,
         r"""The present values of the 24 repayments must add up to the €10,000 borrowed. Each repayment is discounted back to the start: $\dfrac{A}{1.005^k}$. (A) ignores interest altogether; (D) grows the repayments instead of discounting them.

**Answer:** C"""),
    part("(b)", 1, r"""Find $A$.""",
         "443.21", "numeric", EURO, 15,
         r"""The right-hand side of (C) is a geometric series with $a = \dfrac{A}{1.005}$, $r = \dfrac{1}{1.005}$, $n = 24$. Summing it, or using the amortisation formula from the tables:

$$A = 10000 \times \frac{0.005(1.005)^{24}}{(1.005)^{24} - 1} = 443.21$$

**Answer:** €443.21"""),
])

PERPETUITY = question(r"""A payment that goes on forever is an infinite geometric series. Its present values have common ratio $r = \dfrac{1}{1 + i}$, which is less than 1, so the tables' $S_\infty = \dfrac{a}{1 - r}$ applies.""", [
    part("(a)", 0, r"""A scholarship pays €1,000 at the end of every year, forever. Money earns 5% per annum. The present values of the payments form a geometric series. Find its common ratio, correct to three decimal places.""",
         "0.952", "numeric", "A decimal to 3 places (e.g., 0.875)", 5,
         r"""Each payment is one year further away, so each present value is the previous one divided by $1.05$:

$$r = \frac{1}{1.05} = 0.952$$

**Answer:** $0.952$"""),
    part("(b)", 1, r"""How much must be invested now to fund the scholarship forever?""",
         "20000", "numeric", EURO, 15,
         r"""$a = \dfrac{1000}{1.05}$ and $r = \dfrac{1}{1.05}$:

$$S_\infty = \frac{a}{1 - r} = \frac{1000/1.05}{1 - 1/1.05} = \frac{1000/1.05}{0.05/1.05} = \frac{1000}{0.05} = 20000$$

Check: 5% of €20,000 is exactly €1,000 a year, so the fund never runs down.

**Answer:** €20,000"""),
])

# ---------------------------------------------------------------------------

SUBTOPICS = [
    ("10.1 Present Value", 1, [PV_SINGLE, PV_COMPARE, PV_STREAM, PV_RATE]),
    ("10.2 Compound Interest: Loans and Investments", 2, [
        existing("€800 is borrowed for 3 years at 6% simple interest",
                 {"€944 or $944$": "944"}),
        existing("is invested at 4.5% compounded annually",
                 {"Answer: €2492.36": "2492.36"}),
        AER_FROM_MONTHLY, MONTHLY_FROM_AER, DOUBLING, AMORTISATION,
    ]),
    ("10.3 Depreciation (Reducing-Balance Method)", 3, [DEP_VALUE, DEP_RATE, DEP_COMPARE]),
    ("10.4 Applications and Problems Involving Geometric Series", 4, [
        SAVINGS_SERIES, LOAN_SERIES, PERPETUITY,
        existing("Niamh has saved to buy a car"),
    ]),
]

#: Sections this layout replaces. Emptied by the move, then deleted.
# The 2013 exam question's section is called "Exam Question (2013)" on
# production and "2013 Paper 1" locally; same slug, so either name goes.
RETIRED_SECTIONS = ("Exam Question (2013)", "2013 Paper 1", "Compound Interest",
                    "Simple Interest")

#: Every new question with the label the answer checker keys it on.
NEW_QUESTIONS = {
    "PV_SINGLE": PV_SINGLE, "PV_COMPARE": PV_COMPARE, "PV_STREAM": PV_STREAM,
    "PV_RATE": PV_RATE, "AER_FROM_MONTHLY": AER_FROM_MONTHLY,
    "MONTHLY_FROM_AER": MONTHLY_FROM_AER, "DOUBLING": DOUBLING,
    "AMORTISATION": AMORTISATION, "DEP_VALUE": DEP_VALUE, "DEP_RATE": DEP_RATE,
    "DEP_COMPARE": DEP_COMPARE, "SAVINGS_SERIES": SAVINGS_SERIES,
    "LOAN_SERIES": LOAN_SERIES, "PERPETUITY": PERPETUITY,
}


def _first_prompt(question_row):
    first = question_row.parts.order_by("order").first()
    return first.prompt if first else ""


class Command(BaseCommand):
    help = "Add or update the Finance practice questions, by subtopic"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true",
                            help="Report what would change without writing anything")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        subject = Subject.objects.get(name=SUBJECT_NAME)

        with transaction.atomic():
            topic = Topic.objects.get(name=TOPIC_NAME, subject=subject)
            self.stdout.write(f'Found topic "{topic.name}"')
            rows = list(Question.objects.filter(topic=topic).prefetch_related("parts"))

            sections = {}
            for name, order, _ in SUBTOPICS:
                section, made = Section.objects.get_or_create(
                    topic=topic, name=name, defaults={"order": order})
                if section.order != order:
                    section.order = order
                    section.save(update_fields=["order"])
                sections[name] = section
                if made:
                    self.stdout.write(f"  created section {name}")

            # Pass 1: find each existing question and park it at a high order,
            # so no two questions share a position mid-move.
            moved, fixed, placed = 0, 0, []
            for name, _, entries in SUBTOPICS:
                for position, entry in enumerate(entries, start=1):
                    if "existing" not in entry:
                        continue
                    matches = [q for q in rows if entry["existing"] in _first_prompt(q)]
                    if len(matches) != 1:
                        raise SystemExit(f'Expected one question containing '
                                         f'"{entry["existing"]}", found {len(matches)}')
                    q = matches[0]
                    if q.section_id != sections[name].id or q.order != position:
                        Question.objects.filter(pk=q.pk).update(
                            section=sections[name], order=1000 + position)
                        moved += 1
                    placed.append((q.pk, position))
                    for old, new in entry["answer_fixes"].items():
                        fixed += QuestionPart.objects.filter(question=q, answer=old).update(answer=new)
            for pk, position in placed:
                Question.objects.filter(pk=pk).update(order=position)

            # Pass 2: write the new questions into their positions.
            questions = parts = created = 0
            for name, _, entries in SUBTOPICS:
                for position, entry in enumerate(entries, start=1):
                    if "existing" in entry:
                        continue
                    row, made = Question.objects.update_or_create(
                        topic=topic, section=sections[name], order=position,
                        defaults={
                            "hint": entry["hint"], "solution": entry["solution"],
                            "is_copyrighted": entry["is_copyrighted"],
                            "is_exam_question": entry["is_exam_question"],
                            "is_quickkick_suitable": entry["is_quickkick_suitable"],
                        },
                    )
                    questions += 1
                    created += made
                    for p in entry["parts"]:
                        QuestionPart.objects.update_or_create(
                            question=row, label=p["label"],
                            defaults={
                                "prompt": p["prompt"], "answer": p["answer"],
                                "expected_format": p["expected_format"],
                                "solution": p["solution"],
                                "expected_type": p["expected_type"],
                                "max_marks": p["max_marks"], "order": p["order"],
                                "solution_unlock_after_attempts": p["unlock"],
                                "scale": p["scale"], "is_quickkick_suitable": p["qk"],
                            },
                        )
                        parts += 1
                self.stdout.write(f"  {name}: {len(entries)} questions")

            for name in RETIRED_SECTIONS:
                old = Section.objects.filter(topic=topic, name=name).first()
                if not old:
                    continue
                if Question.objects.filter(section=old).exists():
                    self.stderr.write(self.style.WARNING(
                        f'  section "{name}" still has questions; left in place'))
                else:
                    old.delete()
                    self.stdout.write(f'  removed empty section "{name}"')

            if dry_run:
                transaction.set_rollback(True)

        prefix = "Would write" if dry_run else "Wrote"
        self.stdout.write(self.style.SUCCESS(
            f"\n{prefix} {questions} new-content questions ({parts} parts, {created} created); "
            f"{moved} existing questions moved, {fixed} stored answers fixed."))
