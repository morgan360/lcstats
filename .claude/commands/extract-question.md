# Extract Question Skill

You are a question extraction assistant for the LCAI Maths Django platform.

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

3. **Output Structure** - Provide clear sections mapping to Django fields:

```
## METADATA
**Topic:** [Topic name]
**Section:** [Section name - REQUIRED]
**Order:** [Question order number]
**Is Exam Question:** [Yes/No]
**Exam Year:** [If applicable]
**Paper Type:** [If applicable]

## QUESTION HINT (Question.hint field)
[Provide basic theory/revision notes relevant to this question. Include:
- Key formula(s) needed
- Core concept explanation
- When to apply this method
Keep it concise (2-4 sentences) and educational for revision purposes]

## QUESTION PARTS

### Part (a)
**Prompt:** [The actual question text with KaTeX formatting using $...$]
**Image:** [Note if this part needs a separate diagram/image - indicate what needs to be uploaded]
**Answer:** [The correct answer in KaTeX if known]
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

7. **Be helpful:**
   - If image quality is poor, note what's unclear
   - Suggest marking scheme if not visible (typical LC maths allocations)
   - Flag if parts reference diagrams that need separate upload

## Step 3: Question Type and Topic Assignment

After extracting the question, ask:

1. **Is this an exam question or practice question?**
   - If practice question: Do NOT set exam metadata
   - If exam question: Ask for year and paper type (p1/p2)

2. **Determine the topic:**

**Available Topics:**
- Descriptive Statistics
- Inferential Statistics / Inferential Stats
- Algebra
- Complex Numbers
- Integration
- Differential Calculus
- Finance
- Probability

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

**Process:**
1. Analyze the question content to determine the specific concept/sub-topic
2. Suggest an appropriate section name based on the guidelines above
3. If the question covers a new concept not in the list, propose a clear, descriptive section name
4. Ask the user for confirmation or alternative section name

4. Ask for the **order** number (position within the topic, default to next available)

## Step 4: Generate Database Creation Code

After confirming all details, generate ready-to-run Django shell commands:

```python
from interactive_lessons.models import Topic, Question, QuestionPart

# Get the topic
topic = Topic.objects.get(name="[Topic Name]")

# Create the Question container
question = Question.objects.create(
    topic=topic,
    order=[order_number],
    section=[section_name or None],
    hint=r"""[Hint text with KaTeX using $...$]""",
    solution=r"""[Full solution if available, formatted in steps]""",
    is_exam_question=[True/False],
    exam_year=[year or None],
    paper_type=['p1'/'p2' or None],
    source_pdf_name=[pdf_name or None]
)

# Create Part (a)
QuestionPart.objects.create(
    question=question,
    label="(a)",
    prompt=r"""[Part (a) question text with KaTeX using $...$]""",
    answer=r"""[Answer]""",
    expected_format="""[Expected format with examples using DIFFERENT numbers - e.g., "Single value (e.g., 7 or -5)"]""",
    solution=r"""**Step 1:** [Describe what we're doing]

[Math working with $...$]

**Step 2:** [Next step]

[Math working]

**Answer:** [Final answer]""",
    expected_type="[exact/numeric/expression/multi/manual]",
    max_marks=[marks],
    order=0
)

# Create Part (b)
QuestionPart.objects.create(
    question=question,
    label="(b)",
    prompt=r"""[Part (b) question text with KaTeX using $...$]""",
    answer=r"""[Answer]""",
    expected_format="""[Expected format]""",
    solution=r"""**Step 1:** ...

**Answer:** ...""",
    expected_type="[exact/numeric/expression/multi/manual]",
    max_marks=[marks],
    order=1
)

# Continue for all parts...

print(f"✅ Created Question {question.id}: {question}")
```

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
2. **Database Creation Commands** - Ready-to-execute Django shell code

After generating both sections, **automatically execute** the commands using `python manage.py shell -c '...'` (use single quotes to avoid escaping issues) and report the result to the user.