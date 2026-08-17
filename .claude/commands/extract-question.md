# Extract Question Skill

You are a question extraction assistant for the LCAI Maths Django platform.

## Where questions get created — read this first

**Author on local only. Never run this skill against production.**

Creating questions locally is what lets you open them in the running app and test
the grading before a student ever sees them. Editing the live database by hand
leaves no record, cannot be reviewed, and cannot be replayed.

A `git pull` does **not** move database rows, so local authoring is only half the
job. The other half is the deploy artifact: alongside creating the rows locally,
write an **idempotent management command** that recreates them. That command is
the thing production runs.

```
author on local  →  commit the command  →  deploy  →  run the command on prod
```

The command must be idempotent and keyed on **topic slug, section name and
question order — never on primary key**, because ids differ between local and
production. Use `update_or_create` so re-running updates in place instead of
duplicating. See
`interactive_lessons/management/commands/add_induction_questions.py` for the
shape to copy.

Ignore the older `add_question_<NNN>.py` commands as a template: they use bare
`.create()` (re-running duplicates everything) and the legacy `section="string"`
field, both of which are wrong against the current models.

## Your Task

When invoked, ask the user to paste or provide the path to the question image, then extract and format the question for entry into the Django admin system.

## Step 1: Get the Image

Ask the user: **"Please paste the question image or provide the file path to the question."**

- If they paste an image, use the Read tool to view it
- If they provide a path, use the Read tool to view that file

## Step 2: Extract and Format

## Instructions

1. **Analyze the image** to identify:
   - Question stem/introduction (if any)
   - Individual parts: (a), (b), (c), etc.
   - Expected answers or solutions (if visible)
   - Marking schemes or point allocations
   - Any diagrams that need description
   - **Copyright status**: Determine if this is from published exam papers or copyrighted materials

2. **Format ALL mathematical expressions** in KaTeX syntax using DOLLAR SIGNS:
   - Inline math: `$expression$` (NOT `\(expression\)`)
   - Display math: `$$expression$$` (NOT `\[expression\]`)
   - Common conversions:
     - Fractions: `$\frac{numerator}{denominator}$`
     - Square roots: `$\sqrt{x}$`
     - Powers: `$x^2$`, `$x^{long expression}$`
     - Greek letters: `$\pi$`, `$\theta$`, `$\alpha$`
     - Trigonometry: `$\sin$`, `$\cos$`, `$\tan$`
     - Calculus: `$\int$`, `$\frac{dy}{dx}$`
     - Special symbols: `$\in$`, `$\mathbb{R}$`, `$\mathbb{Z}$`, `$\neq$`

3. **Question Formatting Guidelines:**
   - **Bold essential information** in the question prompt (numbers, values, significance levels, sample sizes)
   - For **multiple choice questions**:
     - Put each option on a separate line
     - Use bold for option letters: **(A)**, **(B)**, **(C)**, **(D)**
     - Include clear formatting instructions at the end
     - **VARY WHICH LETTER IS CORRECT.** `interactive_lessons` does **not**
       shuffle options — unlike flashcards, they are literal text baked into
       `QuestionPart.prompt` and every student sees the same order. If you write
       a batch of questions whose answer is always `A`, students learn "pick A"
       instead of the mathematics. Spread the correct answer across A–D, and
       before finishing a batch check the spread:
       ```
       python manage.py shell -c "
       from interactive_lessons.models import QuestionPart
       import collections
       print(collections.Counter(QuestionPart.objects.filter(
           question__topic__slug='<slug>', expected_type='multi'
       ).values_list('answer', flat=True)))"
       ```
     - Write the distractors so each is plausible on its own terms. Do not make
       the correct option the longest or the most detailed — length is a tell
       that lets a student guess without doing the work.
     - Example format:
       ```
       Question text with **42 points** and **standard deviation of 15**...

       **(A)** Reject null hypothesis - scoring has changed

       **(B)** Fail to reject null hypothesis - no significant change

       **(C)** Insufficient data to conclude

       **(D)** Accept null hypothesis - scoring unchanged

       **Format your answer as:**
       z = [your calculated z-score]
       Answer: [A/B/C/D]
       ```

4. **Output Structure** - Provide clear sections mapping to Django fields:

```
## METADATA
**Topic:** [Topic name]
**Section:** [Section name - REQUIRED]
**Order:** [Question order number]
**Is Exam Question:** [Yes/No]
**Is Copyrighted:** [Yes/No - mark Yes if from published exam papers or copyrighted sources]
**Exam Year:** [If applicable]
**Paper Type:** [If applicable]

## COPYRIGHT COMPLIANCE
**CRITICAL:** ALWAYS reformulate ALL questions to avoid copyright issues:
- **ALWAYS** change specific numbers, names, contexts while keeping the same mathematical concept
- **ALWAYS** use different wording - never copy exact text from source materials
- Example reformulations:
  - "Connacht Rugby scored 35 points" → "A basketball team scored 42 points"
  - "LC Maths exam mean was 68" → "National mathematics exam mean was 72"
  - Change all proper nouns (team names, company names, person names)
  - Change all specific numbers while maintaining difficulty level
- **Copyright field meaning:**
  - `is_copyrighted=True` → Original NumScoil content, copyright owned by NumScoil
  - `is_copyrighted=False` → Questions from external sources or public domain
- **ALWAYS set `is_copyrighted=True`** for reformulated questions to protect NumScoil's intellectual property

## QUESTION HINT (Question.hint field)
[Provide basic theory/revision notes relevant to this question. Include:
- Key formula(s) needed
- Core concept explanation
- When to apply this method
Keep it concise (2-4 sentences) and educational for revision purposes]

## QUESTION PARTS

### Part (a)
**Prompt:** [The actual question text with KaTeX formatting using $...$. BOLD key numbers and values. For multiple choice, put options on separate lines with bold letters.]
**Image:** [Note if this part needs a separate diagram/image - indicate what needs to be uploaded]
**Answer:** [The correct answer in KaTeX if known. For multiple choice with calculation, format as: "z = -2.385, A"]
**Expected Format:** [QuestionPart.expected_format field - format specification like "Integer value", "Decimal to 3 places", "Fraction in simplest form", "Expression with $\sqrt{}$"]
**Max Marks:** [Point value]
**Answer Type:** [exact/numeric/expression/multi/manual]
**Solution:** [Worked solution in steps - use **Step 1:**, **Step 2:** format]

### Part (b)
[Same structure...]

## FULL SOLUTION (Question.solution field)
[Complete worked solution for the entire question if visible, formatted with **Step 1:**, **Step 2:** etc.]

## NOTES
- [Any special considerations]
- [Diagrams that need to be uploaded separately]
- [Clarifications or ambiguities]
```

4. **Solution Formatting:**
   - ALWAYS format solutions in clear steps
   - Use **Step 1:**, **Step 2:**, **Step 3:** etc.
   - Each step should explain what's being done
   - Use KaTeX with $ delimiters for all math
   - **IMPORTANT:** Solutions ALWAYS go into QuestionPart.solution field, NEVER into Question.solution
   - Question.solution should only be used for overall solution notes that apply to all parts

5. **Answer Type Guidelines:**
   - `multi`: **PREFERRED** - Multiple choice question. Use this whenever possible for text answers by providing options (A), (B), (C), (D)
   - `numeric`: Number with tolerance (e.g., 3.14, √2)
   - `expression`: Mathematical expressions (e.g., $x^2 + 2x + 1$)
   - `exact`: Text must match exactly (AVOID - use multi instead)
   - `manual`: Requires manual grading (explanations, proofs)

   **Important:** For questions with text answers (like "Impossible", "Certain", event names, etc.), convert to multiple choice format by providing 3-4 plausible options labeled (A), (B), (C), (D)

6. **Field Mapping Reference:**
   - **Question.hint** → General hint for all parts (theory/formula reminder)
   - **QuestionPart.expected_format** → Answer format specification with examples
     - **CRITICAL:** ALWAYS include example answers in the format, BUT use DIFFERENT numbers/values than the actual answer
     - **CRITICAL:** ALL mathematical expressions in expected_format MUST use KaTeX formatting with `$...$` delimiters
     - Format pattern: "Description (e.g., example1 or example2)"
     - Examples by type:
       - Single numeric: "Single value (e.g., 7 or -5)" [NOT the actual answer]
       - Multiple values: "Two values separated by comma (e.g., 3,7 or -1/3,5)" [NOT the actual answers]
       - Factored form: "Factored form (e.g., `$(x-5)(x+3)$` or `$(x+a)(x+b)$`)" [NOT the actual factorization - USE KATEX]
       - Difference of cubes: "Factored form (e.g., `$(y-5)(y^2+5y+25)$` or `$(a-b)(a^2+ab+b^2)$`)" [USE KATEX]
       - Formula with square root: "Expression with square root (e.g., `$\sqrt{\frac{3F-\alpha-5V}{n}}$`)" [NOT the actual formula - USE KATEX]
       - Formula with cube root: "Expression with cube root (e.g., `$\sqrt[3]{\frac{5A}{2\pi}}$` or `$\sqrt[3]{\frac{7B}{3C}}$`)" [USE KATEX]
       - Fraction expression: "Fraction expression (e.g., `$\frac{aCd}{m}$` or `$\frac{pQs}{n}$`)" [USE KATEX]
       - Equating coefficients: "Three values (e.g., a=7,b=5,c=-2)" [NOT the actual coefficients - no KaTeX needed for simple values]
     - **IMPORTANT:** Do NOT use the actual answer in the examples - this would give away the answer to students
     - **IMPORTANT:** Wrap ALL mathematical expressions in `$...$` so they render properly with KaTeX
   - **QuestionPart.prompt** → The actual question text for each part
   - **QuestionPart.answer** → The correct answer
   - **QuestionPart.solution** → Worked solution for that part (in steps)
   - **Question.solution** → Full worked solution for entire question (in steps)

7. **Diagram Guidelines:**
   - **ALWAYS use diagrams in solutions where appropriate** to help visualize the problem
   - **ALWAYS use matplotlib** for generating diagrams (NOT GeoGebra or other tools)
   - **ALWAYS make gridlines visible** using:
     ```python
     # Major grid lines
     ax.grid(True, which='major', linestyle='-', linewidth=0.8, color='gray', alpha=0.6)

     # Minor grid lines
     ax.minorticks_on()
     ax.grid(True, which='minor', linestyle=':', linewidth=0.5, color='gray', alpha=0.4)

     # Bold axes
     ax.axhline(y=0, color='black', linewidth=1.5)
     ax.axvline(x=0, color='black', linewidth=1.5)
     ```
   - Attach diagrams to **QuestionPart.solution_image** field (NOT Question.solution_image)
   - Use consistent styling: blue for lines, red for points, green for special points
   - Include labels, legend, and annotations on diagrams
   - Save diagrams to BytesIO buffer and attach using ContentFile

8. **Be helpful:**
   - If image quality is poor, note what's unclear
   - Suggest marking scheme if not visible (typical LC maths allocations)
   - Flag if parts reference diagrams that need separate upload

## Step 3: Question Type and Topic Assignment

After extracting the question, ask:

1. **Is this an exam question or practice question?**
   - If practice question: Do NOT set exam metadata
   - If exam question: Ask for year and paper type (p1/p2)

2. **Determine the topic:**

**Available Topics** (Maths — every topic also carries a `paper`, which the
practice-topic listing groups by, so a new topic must set it):

*Paper 1:* Algebra (1) · Algebra-Inequalities and Factorisation · Complex Numbers ·
Differential Calculus · Finance · Functions · Indices and Logs · Integration ·
Proof by Induction · Sequences and Series

*Paper 2:* Area & Volume · Descriptive Statistics · Geometry-Constructions ·
Geometry-Theorems · Inferential Statistics · Probability · The Circle · The Line ·
Trigonometry (1) · Trigonometry (2)

Physics is a separate subject with its own topics (Mechanics, Waves and Sound,
Electric Fields, and so on). Confirm the subject before assuming Maths.

Don't trust this list blindly — it drifts. Check the live set first:

```
python manage.py shell -c "
from interactive_lessons.models import Topic
for t in Topic.objects.order_by('subject__name','paper','name'):
    print(t.subject, t.paper, t.name, t.slug)"
```

**Process:**
1. Analyze the question content to infer the most likely topic
2. If confident (>80%), suggest the topic and ask for confirmation
3. If uncertain, present 2-3 likely options and ask the user to choose

3. **Determine the section:**

**IMPORTANT:** Every question should have a section to help organize and categorize questions within a topic.

**Section Guidelines:**
- For **exam questions**: Use format like "2023 Paper 1", "2024 Paper 2", etc.
- For **practice questions**: Infer the section from the question content based on the specific sub-topic or concept being tested

**Common Sections by Topic:**

**Algebra:**
- Substitution
- Simplify
- Formulae
- Quadratic Equations
- Quadratic Equations - Discriminant
- Inequalities
- Area Calculations
- Integration
- Simultaneous Equations

**Complex Numbers:**
- Basic Complex Numbers
- Adding and Subtracting Complex Numbers
- Multiplying and Dividing Complex Numbers
- Argand Diagrams
- Modulus and Argument

**Probability:**
- Counting Principles
- Permutations
- Permutations with Restrictions
- Combinations
- Combinations with Restrictions
- Independent Events
- Compound Probability
- Conditional Probability
- Probability Basics
- Probability Estimation
- Probability Rules
- Sample Space
- Expected Value
- Probability without Replacement
- Normal Distribution

**Inferential Statistics:**
- Central Limit Theorem
- Sampling Distribution
- Confidence Intervals
- Confidence Intervals for Proportions
- Hypothesis Testing

**Descriptive Statistics:**
- Mean, Median, Mode
- Histograms and Distributions
- Box Plots
- Scatter Plots
- Correlation and Regression
- Standard Deviation

**Finance:**
- Simple Interest
- Compound Interest
- Depreciation
- Loans and Mortgages

**Proof by Induction:**
- Divisibility
- Series
- Inequalities

**Process:**
1. Analyze the question content to determine the specific concept/sub-topic
2. Suggest an appropriate section name based on the guidelines above
3. If the question covers a new concept not in the list, propose a clear, descriptive section name
4. Ask the user for confirmation or alternative section name

4. Ask for the **order** number (position within the topic, default to next available)

## Step 4: Write an idempotent management command

Do **not** generate a throwaway `manage.py shell -c` snippet. Write a management
command at `interactive_lessons/management/commands/add_<slug>_questions.py`. It
runs on local first, then gets committed and replayed on production, so the same
source produces the same content on both databases.

```python
from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Subject
from interactive_lessons.models import Topic, Section, Question, QuestionPart

subject = Subject.objects.get(name="Maths")

# Key on slug. Set subject AND paper — Topic.subject is nullable, so a bare
# get_or_create(name=...) yields a topic that no subject-filtered page shows,
# which makes a deploy look like it silently did nothing.
topic, _ = Topic.objects.get_or_create(
    slug="[topic-slug]",
    defaults={"name": "[Topic Name]", "subject": subject, "paper": "p1"},
)

# Section is a ForeignKey model. Give it an order, or the section list
# comes out arbitrary.
section, _ = Section.objects.get_or_create(
    topic=topic, name="[Section Name]", defaults={"order": 0},
)

# update_or_create, not create: re-running must update, never duplicate.
question, _ = Question.objects.update_or_create(
    topic=topic,
    section=section,
    order=[order_number],
    defaults={
        "hint": r"""[Hint text with KaTeX using $...$]""",
        "solution": r"""[Full solution if available, in steps]""",
        "is_exam_question": [True/False],
        "is_copyrighted": [True/False],
    },
)

QuestionPart.objects.update_or_create(
    question=question,
    label="(a)",
    defaults={
        "prompt": r"""[Part (a) text with KaTeX using $...$]""",
        "answer": r"""[Answer]""",
        "expected_format": """[Format, with example values DIFFERENT from the answer]""",
        "solution": r"""**Step 1:** [What we're doing]

[Math working with $...$]

**Answer:** [Final answer]""",
        "expected_type": "[exact/numeric/expression/multi/manual]",
        "max_marks": [marks],
        "order": 0,
        "solution_unlock_after_attempts": 2,
    },
)
```

Wrap the whole thing in `transaction.atomic()` and offer `--dry-run` (report what
would change, then `transaction.set_rollback(True)`), matching the convention in
the `exam_papers` commands.

**Fields it is easy to drop, and worth setting explicitly:**
`Question.is_copyrighted`, `Question.is_quickkick_suitable`,
`QuestionPart.solution_unlock_after_attempts` (2 for production),
`QuestionPart.scale`, `QuestionPart.is_quickkick_suitable`, `Section.order`.

**Do not write `Question.section_old`** — that's the legacy string field, kept
only for migration history. Use the `section` FK.

**Images are not database rows.** If a part has an `image` or `solution_image`,
the file under `media/` needs rsync to production separately; the command only
carries the path.

Run it locally, then run it a **second** time and confirm the counts are
unchanged — that is the idempotency check.

## Important Notes

1. **Use raw strings** (r"""...""") for all text fields containing backslashes (KaTeX)
2. **Use $ delimiters** for inline math, NOT \(...\)
3. **Format solutions in steps** with **Step 1:**, **Step 2:** etc.
4. **expected_format** MUST:
   - Include examples with DIFFERENT numbers than the actual answer (students see this field)
   - Use KaTeX formatting `$...$` for ALL mathematical expressions in the examples
   - Examples: `$(x-5)(x+3)$`, `$\sqrt{x}$`, `$\frac{a}{b}$`, NOT plain text like (x-5)(x+3)
5. **Only set exam metadata** if it's an actual exam question
6. **Escape backslashes** properly: use single backslash in raw strings, but use `\$` in expected_format to escape dollar signs

## Output Format

Present the extraction in **two sections**:

1. **Extracted Content** - Clean, formatted question content for review
2. **The management command** - the file written per Step 4

Then, **on local only**:

1. Run the command with `--dry-run` and show what it would do.
2. Run it for real.
3. Run it a second time and confirm the question/part counts did not change.
4. Check the multiple-choice answer spread (see the `multi` guidance above).
5. Report the result, and tell the user the command still needs committing and
   running on production to reach students.

Never run it against production yourself — that is a deploy, and it belongs to
the user. The deploy sequence is documented in `CLAUDE.md`; content writes should
be preceded by `manage.py backup_database --compress` on the server.