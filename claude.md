# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

NumScoil is a Django-based web application providing an AI-powered interactive tutor for Leaving Certificate Honours students. The system supports **multiple subjects** (currently Maths and Physics) and combines question-based learning with OpenAI integration for grading, hints, and contextual help.

**Tech Stack:**
- Django 5.2.7 with MySQL backend (database: `lcaim`)
- OpenAI API (GPT-4o-mini for grading/chat, text-embedding-3-small for RAG)
- LangChain for retrieval-augmented generation
- MarkdownX and markdown-katex for LaTeX rendering
- FAISS for vector similarity search

## Architecture

### Django Apps Structure

`core` (subjects + `SubjectMiddleware`), `interactive_lessons`, `students`,
`exam_papers`, `studyplans`, `homework`, `homework_check`, `notes` (RAG),
`flashcards`, `quickkicks`, `home` (news), `chat`, `cheatsheets`, `revision`,
`reports`, `schools`, `stats_simulator`.

Two things `ls` and the models will not tell you:

- **Every content query filters by `request.current_subject`.** Topics and exam
  papers belong to a Subject, and `core.middleware.SubjectMiddleware` tracks
  which one the session is in.
- **Exam questions are set and listed whole.** Homework, study-plan items and
  Badge Tests hand out whole questions; older `exam_part` homework tasks and
  plan items still exist and still complete when that part alone is attempted,
  but nothing creates new ones.

### Key Architectural Patterns

**Multi-part Question System:**
- `Question` acts as a container/stem with optional intro text and solution image
- `QuestionPart` holds actual sub-questions (e.g., (a), (b)), each with own prompt, answer, hint, solution, and marking scheme
- Supports multiple answer types: exact, numeric, algebraic expression, multiple choice
- **Solution Access Control**: Solutions unlock after threshold attempts (default: 2) or when student gets correct answer
  - `QuestionPart.solution_unlock_after_attempts` (default: 2 for production)
  - Set to 0 for always-visible solutions
  - Same system as exam questions

**Grading Pipeline** (`interactive_lessons/stats_tutor.py`):
1. Numeric normalization (handles fractions, decimals, degrees→radians, π)
2. Algebraic comparison fallback (via `compare_algebraic`)
3. GPT-4o-mini grading if both fail
4. Penalty deductions for hint/solution usage (-20%, -50%)

**RAG System** (`notes/`):
- Notes auto-embed on save using OpenAI embeddings (cached by MD5 hash)
- `match_note()` retrieves similar notes via cosine similarity
- If confidence < threshold (default 0.7), falls back to GPT with context from top 3 notes
- InfoBot view (`interactive_lessons/views.py:info_bot`) handles student queries

**Student Progress:**
- Each `QuestionAttempt` links to both `Question` and `QuestionPart`
- `StudentProfile.update_progress()` recalculates total score and distinct topics completed
- Marks auto-calculated: `(score_awarded / 100) * max_marks`

**Exam Papers System:**
- **Two Access Paths**:
  1. **Exam Papers** (`/exam-papers/`) - Full timed exam mode only (150 min timer)
  2. **Interactive Lessons → Exam Questions** - Individual question practice (suggested time per question)
- **Dual Timer Display**: When in timed exam mode + question has suggested time, both timers show
- **Attempt Modes**:
  - `full_timed` - Complete exam with 150-minute countdown, auto-submits when time expires
  - `question_practice` - Individual questions with suggested time (no forced submission)
- **Solution System**:
  - Solution images uploaded to `ExamQuestionPart.solution_image` (from marking schemes)
  - Full marking scheme PDFs uploaded to `ExamPaper.marking_scheme_pdf` (accessible anytime)
  - Solutions unlock after: correct answer OR attempts >= threshold OR threshold = 0
- **Shared Grading**: Exam questions use same `mark_student_answer()` from `stats_tutor.py`
- **One level of parts**: a part is a letter — `(a)`, `(b)` — never `(a)(i)`, and a student answers it in one box. Sub-parts are gone from the data; only the official scheme PDFs still print (i)/(ii) rows, which the scheme reader in `exam_papers/utils.py` has to understand.
- **Topic Linking**: each `ExamQuestion` has a main `topic`, an optional `secondary_topic` (listed under it only when `list_under_secondary` is ticked) and an optional `need_to_know_topic` (a minor part: shown on the question, never listed). `topic_filter` in `exam_papers/services/topic_questions.py` is the one listing rule, used by topic pages, the Exam Questions index, the homework picker and the worksheet. `ExamQuestionPart.topic` is still filled by `tag_part_topics` but only feeds `tag_question_topics`, which ranks a question's topics by part marks to fill blank slots (secondary ticked at ≥ ⅓ of the marks). `?part=<id>` still opens one part, for older part tasks.
- **One marking-scheme image per part**: `ExamQuestionPart.solution_image`, covering the whole letter, (i)–(iv) included. `extract_solution_images` cuts it with `letter_region`, which merges every scheme row for the letter. Read through `part.solution_images` — that is what the grader, the printable sheets and the PDFs use.
- **Retagging**: `/exam-papers/worksheet/` carries a per-card main / secondary (+ "List under it") / need-to-know editor for **superusers only** (`exam_papers/topic_editing.py`); the save endpoint re-checks, so hiding the control is not the access control.

**News & Announcements System** (`home/models.py:NewsItem`):
- **Audience Targeting**:
  - **General announcements**: Leave `target_classes` empty → visible to all students
  - **Class-specific**: Link to `TeacherClass` → only visible to enrolled students
  - Users only see announcements for their enrolled classes + general announcements
- **Publishing Controls**:
  - `publish_date`: When announcement becomes visible
  - `expiry_date`: Optional automatic expiration
  - `is_pinned`: Pinned items appear at top
  - `is_dismissible`: If False, students cannot dismiss (for critical announcements)
- **Categories**: general, new_content, tips, system, event
- **Tracking**: `dismissed_by` tracks which students have dismissed each announcement
- **Content**: Supports Markdown with LaTeX via MarkdownX
- **Method**: `NewsItem.get_active_for_user(user)` returns filtered, active announcements

## Common Development Commands

The standard Django and npm invocations all work as you would expect. Two
things that are not standard:

```bash
source .venv/bin/activate   # .venv, not venv
npm run watch:css           # run alongside runserver when editing templates
```

`.env` is required and `SECRET_KEY` has no fallback -- `.env.example` lists the
rest. Most apps still carry stub `tests.py` files, so a green suite is weaker
evidence here than it looks: prefer adding a test to trusting the coverage.

### Custom Management Commands

This project has a dozen of its own `manage.py` commands, several with traps
their `--help` does not mention. They live in the **`project-commands`** skill;
read it before running any of them.

### Database
- **MySQL connection**: `lcaim` database on localhost:3306
- **Credentials**: in `.env` / `lcstats/settings.py` -- never repeated here
- **Data Entry**: Questions are added via Django Admin (`/admin/`), not fixtures
- **Direct Access**: Use Django ORM or MySQL client for queries

### Migration Patterns

**CRITICAL - Migration Safety:**
- Fresh installations may have different schema than migrated databases
- Migrations 0016 and 0017 include defensive checks for column existence
- When writing data migrations that reference old columns, always check if column exists first:
```python
with connection.cursor() as cursor:
    cursor.execute("""
        SELECT COUNT(*) FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'your_table'
        AND COLUMN_NAME = 'old_column'
    """)
    column_exists = cursor.fetchone()[0] > 0

if not column_exists:
    return  # Skip for fresh installations
```
- This prevents errors when migrations reference fields removed in later migrations

## Data Flow & User Journey

### Student Registration & Authentication
1. **Registration requires valid code**: `students/models.py:RegistrationCode`
   - **Two code types**: `student` and `teacher`
   - **Student codes**:
     - Creates regular user accounts (not staff)
     - Can be linked to a `TeacherClass` for auto-enrollment
     - When student registers, they're automatically added to the linked class
   - **Teacher codes**:
     - Creates staff user accounts (`is_staff=True`)
     - Automatically creates `TeacherProfile` for homework management
     - Grants access to teacher dashboard and class management
   - Codes created by admin with configurable `max_uses` (0 = unlimited)
   - Signup form validates code via `students/forms.py:SignupFormWithCode`
   - On success: increments `times_used`, creates User + StudentProfile (via signal)
   - **Admin actions**:
     - "Generate 5 Student Codes" - Creates codes with `STU-` prefix
     - "Generate 1 Teacher Code" - Creates code with `TCH-` prefix

2. **Login tracking**:
   - Every login/logout/failed attempt logged in `LoginHistory`
   - Active sessions tracked in `UserSession` (linked to Django's Session)
   - IP address, user agent, and timestamps captured

3. **User workflows**:
   - **Student**: `Signup → Login → Dashboard → Select Topic → Select Section → Answer Questions → Get Hints/Solutions → View Progress`
   - **Teacher**: `Signup → Login → Teacher Dashboard → Create Classes → Create Homework Assignments → Monitor Student Progress`

## Code Patterns to Follow

**When adding new question types:**
- Extend `QuestionPart.expected_type` choices in models
- Update `stats_tutor.py` grading logic to handle new type
- Consider adding specialized comparison in `services/utils_math.py`

**When modifying Notes:**
- Remember embeddings auto-regenerate on save
- Metadata field used for embedding (preferred over full content)
- Check `FAQ_MATCH_THRESHOLD` when tuning retrieval

**When working with LaTeX:**
- Use `interactive_lessons/utils/katex_sanitizer.py` for sanitization
- Questions auto-sanitize on save if containing `(\\` or `[\\`
- Frontend renders via markdown-katex extension

**When working with Exam Papers:**
- **Two question systems exist**: `interactive_lessons.Question` (practice) and `exam_papers.ExamQuestion` (exams)
- Both share the same grading system via `stats_tutor.mark_student_answer()`
- Exam questions MUST link to a Topic (`ExamQuestion.topic`) to appear in Interactive Lessons
- Avoid code duplication: use single question interface (`exam_papers/templates/.../question_interface.html`)
- Attempt mode filtering: `ExamAttempt.objects.filter(attempt_mode='full_timed')` for timed exams only
- Solution unlocking logic: check `has_correct_answer OR attempts >= threshold OR threshold == 0`
- Upload solution images to question parts, marking scheme PDFs to papers (not JSON marking schemes)

**When working with Flashcards:**
- **Mastery Progression**: new → learning → know → retired
- **Multiple Choice Mode** (new, learning, dont_know states):
  - Student selects from 4 shuffled options (1 correct + 3 distractors)
  - Correct on first attempt: new → learning
  - Correct from learning: learning → know
  - 2+ incorrect from learning: learning → dont_know
  - Correct from dont_know: dont_know → learning
- **Self-Assessment Mode** (know state only):
  - Student shown answer, self-assesses if they knew it
  - Self-assessed correct: know → retired (removed from deck)
  - Self-assessed incorrect: stays know (can manually demote to learning)
- Each card has `get_shuffled_options()` method for randomized display
- Progress tracked via `FlashcardAttempt` with `view_count`, `correct_count`, `incorrect_count`

## Production Deployment

Deploying, and the Cloudflare/static-file setup behind it, is in the
**`deploying`** skill. The one rule worth carrying without it: **any change
under `static/` needs `collectstatic` and a wsgi touch on production, or the
file 404s silently** -- the page renders, the `<script>` tag is there, and only
its functions are missing.
