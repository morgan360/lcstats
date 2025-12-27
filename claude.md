# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

NumScoil is a Django-based web application providing an AI-powered interactive tutor for Leaving Certificate Honours Maths students. The system combines question-based learning with OpenAI integration for grading, hints, and contextual help.

**Tech Stack:**
- Django 5.2.7 with MySQL backend (database: `lcaim`)
- OpenAI API (GPT-4o-mini for grading/chat, text-embedding-3-small for RAG)
- LangChain for retrieval-augmented generation
- MarkdownX and markdown-katex for LaTeX rendering
- FAISS for vector similarity search

## Architecture

### Django Apps Structure

The project follows a modular Django app pattern:

1. **`interactive_lessons/`** - Core question/lesson functionality
   - Models: `Topic`, `Question`, `QuestionPart` (multi-part questions with parts like (a), (b), etc.)
   - `stats_tutor.py`: Answer normalization and grading logic (numeric, algebraic, GPT fallback)
   - `services/marking.py`: Primary grading service
   - `services/utils_math.py`: Algebraic comparison utilities

2. **`students/`** - Student tracking and progress
   - Models: `StudentProfile`, `QuestionAttempt`
   - Tracks scores, attempts per question part, and progress across topics
   - Auto-calculates `marks_awarded` based on `score_awarded` and `max_marks`

3. **`exam_papers/`** - Full exam paper system
   - Models: `ExamPaper`, `ExamQuestion`, `ExamQuestionPart`, `ExamAttempt`, `ExamQuestionAttempt`
   - Supports timed exam mode (150 min) and individual question practice
   - Questions link to Topics for practice access from Interactive Lessons
   - Dual timer system: overall exam timer + per-question suggested time
   - Solution images and marking scheme PDFs attached to questions/papers
   - Management command: `extract_exam_questions` for PDF parsing

4. **`notes/`** - RAG-based knowledge system
   - Models: `Note` (auto-embeds on save), `InfoBotQuery` (chat history)
   - `helpers/match_note.py`: Semantic search with threshold-based matching
   - `utils.py`: Vector search utilities using FAISS
   - Notes linked to Topics; embeddings regenerated on content/metadata changes

5. **`chat/`** - Standalone chat interface for AI tutor

6. **`home/`** - Landing pages

7. **`homework/`** - Teacher-student homework assignment system
   - Models: `TeacherProfile`, `TeacherClass`, `HomeworkAssignment`, `HomeworkTask`, `StudentHomeworkProgress`
   - Teachers create assignments with tasks (topics, sections, exam questions, QuickKicks)
   - Students see assignments on dashboard with progress tracking
   - Notification snooze system for homework reminders
   - Auto-calculates completion percentage and overdue status

8. **`quickkicks/`** - Bite-sized practice questions
9. **`revision/`** - Revision materials and resources
10. **`cheatsheets/`** - Quick reference sheets
11. **`stats_simulator/`** - Interactive statistics simulations

### Key Architectural Patterns

**Multi-part Question System:**
- `Question` acts as a container/stem with optional intro text and solution image
- `QuestionPart` holds actual sub-questions (e.g., (a), (b)), each with own prompt, answer, hint, solution, and marking scheme
- Supports multiple answer types: exact, numeric, algebraic expression, multiple choice

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
- **Topic Linking**: `ExamQuestion.topic` links to `Topic` for cross-app integration

## Common Development Commands

### Environment Setup
```bash
# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Environment variables (.env file required)
# OPENAI_API_KEY - OpenAI API key for GPT-4o-mini and embeddings
# OPENAI_ORG_ID - OpenAI organization ID
# SECRET_KEY - Django secret key (REQUIRED - no fallback)
# DEBUG - Set to 'True' for development (defaults to False)
# ALLOWED_HOSTS - Comma-separated list of allowed hostnames
# OPENAI_EMBED_MODEL - Embedding model (default: text-embedding-3-small)
# OPENAI_CHAT_MODEL - Chat model (default: gpt-4o-mini)
# FAQ_MATCH_THRESHOLD - RAG confidence threshold (default: 0.7)
```

### Django Management
```bash
# Run development server
python manage.py runserver

# Database migrations
python manage.py makemigrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Shell access
python manage.py shell

# Collect static files (for production)
python manage.py collectstatic
```

### Custom Management Commands

**Exam Papers:**
```bash
# Download LC exam papers
python manage.py download_lc_papers

# Extract questions from exam PDFs
python manage.py extract_exam_questions

# Extract marking scheme information
python manage.py extract_marking_scheme

# Auto-extract marking info from PDFs
python manage.py auto_extract_marking_info

# Populate answer format fields
python manage.py populate_answer_formats

# Import exam paper (interactive_lessons)
python manage.py import_exam_paper

# Import marking scheme (interactive_lessons)
python manage.py import_marking_scheme
```

**Student Management:**
```bash
# Generate daily student progress report
python manage.py daily_student_report

# Log out all active users
python manage.py logout_all_users
```

### Database
- **MySQL connection**: `lcaim` database on localhost:3306
- **Credentials**: Username: `morgan`, Password: `help1234`
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
   - Codes created by admin with configurable max_uses
   - Signup form validates code via `students/forms.py:SignupFormWithCode`
   - On success: increments `times_used`, creates User + StudentProfile (via signal)

2. **Login tracking**:
   - Every login/logout/failed attempt logged in `LoginHistory`
   - Active sessions tracked in `UserSession` (linked to Django's Session)
   - IP address, user agent, and timestamps captured

3. **Student workflow**:
   ```
   Signup → Login → Dashboard → Select Topic → Select Section →
   → Answer Questions → Get Hints/Solutions → View Progress
   ```

### Question Attempt Flow
```
Student submits answer
  ↓
POST /interactive/<topic>/<section>/question/<n>/
  ↓
views.section_question_view()
  ↓
services/marking.py:grade_submission()
  ↓
1. Try algebraic comparison (utils_math.py)
2. Try numeric normalization (stats_tutor.py)
3. Fall back to GPT-4o-mini
  ↓
Create QuestionAttempt record
  ↓
Auto-calculate marks_awarded (via model save())
  ↓
Update StudentProfile.total_score
  ↓
Return feedback to student
```

### Exam Attempt Flow
```
Start exam → ExamAttempt created (attempt_mode='full_timed')
  ↓
Timer starts (150 min countdown)
  ↓
Student navigates questions → answers saved to ExamQuestionAttempt
  ↓
Timer expires OR student clicks "Complete"
  ↓
ExamAttempt.completed_at set
  ↓
Results page shows score, time taken, answers
```

## URL Structure

- `/` - Home (home app)
- `/admin/` - Django admin
- `/students/` - Student dashboard, login, progress
- `/interactive/` - Question interface, topics
  - `/interactive/<topic-slug>/exam-questions/` - Exam questions for a topic (practice mode)
- `/exam-papers/` - Exam papers list and timed exams
- `/notes/` - Notes management
- `/chat/` - AI chat interface
- `/homework/` - Student/teacher homework interface
- `/markdownx/` - Markdown editor endpoints

## Important Configuration

**settings.py OpenAI Settings:**
- `OPENAI_API_KEY`, `OPENAI_ORG_ID` loaded from `.env`
- `OPENAI_EMBED_MODEL` (default: "text-embedding-3-small")
- `OPENAI_CHAT_MODEL` (default: "gpt-4o-mini")
- `FAQ_MATCH_THRESHOLD` (default: 0.7) - confidence threshold for RAG matches

**Login Redirects:**
- `LOGIN_REDIRECT_URL = '/students/dashboard/'`
- `LOGOUT_REDIRECT_URL = '/students/login/'`

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

## Advanced Architecture Details

### Grading System Deep Dive

The grading pipeline (`interactive_lessons/services/marking.py` → `stats_tutor.py`) is multi-layered:

1. **Algebraic Equivalence** (`services/utils_math.py`):
   - Uses SymPy to parse and simplify expressions
   - Handles implicit multiplication (e.g., `2x` vs `2*x`)
   - Catches `SympifyError` for invalid expressions
   - Returns immediate 100% if algebraically equivalent

2. **Numeric Normalization** (`stats_tutor.py`):
   - Fraction handling: `"3/4"` → `0.75`
   - Decimal cleaning: `"3.14159"` → `3.14` (configurable precision)
   - Angle conversion: degrees ↔ radians
   - π handling: `"2π"` → `6.283...`
   - Tolerance-based comparison for floating point

3. **GPT Fallback** (OpenAI GPT-4o-mini):
   - Triggered when algebraic/numeric methods fail
   - Receives question text, student answer, correct answer
   - Returns score (0-100) and feedback
   - Used for free-text, proof-based, or complex answers

4. **Penalty Application**:
   - Hint used: -20% from final score
   - Solution viewed: -50% from final score
   - Applied AFTER base score calculation

**Entry point:** `grade_submission()` in `services/marking.py`

### Signal System

Django signals auto-trigger side effects (`students/signals.py`):

- **`post_save(User)`**: Auto-creates `StudentProfile` for new users
- **`user_logged_in`**: Creates `LoginHistory` and `UserSession` records
- **`user_logged_out`**: Deletes `UserSession`
- **`user_login_failed`**: Logs failed attempt with IP/user agent
- **`pre_delete(Session)`**: Cleans up orphaned `UserSession`

These run automatically via `students/apps.py` signal registration.

### RAG (Retrieval-Augmented Generation) System

**Embedding Pipeline** (`notes/models.py`):
```python
Note.save() → compute_hash() → check if changed →
  → generate_embedding() → OpenAI API → store in vector_embedding field
```

**Retrieval Pipeline** (`notes/helpers/match_note.py`):
```python
Student query → expand_query() → generate embedding →
  → FAISS similarity search → top_n matches →
  → check threshold →
    if confidence >= threshold: return best note
    else: GPT with top 3 notes as context
```

**Query Expansion**: Short queries like "mean" expanded to "mean average central value sum divided count" for better semantic matching.

### Production Deployment Considerations

**Security (settings.py, lines 56-85):**
- Cloudflare proxy setup: Uses `X-Forwarded-Proto` header for HTTPS detection
- `SECURE_SSL_REDIRECT` disabled to prevent redirect loops with Cloudflare
- HSTS enabled with 1-year expiry, subdomains, and preload
- Session/CSRF cookies marked secure in production
- `X_FRAME_OPTIONS = 'SAMEORIGIN'` to allow video controls

**Static Files:**
- `STATICFILES_DIRS = [BASE_DIR / "static"]` - Development static files
- `STATIC_ROOT = BASE_DIR / "staticfiles"` - Production collected statics
- `MEDIA_ROOT = BASE_DIR / "media"` - User uploads (marking schemes, images)

**Environment Detection:**
- `DEBUG = os.getenv('DEBUG', 'False') == 'True'` - Explicit opt-in for debug mode
- `SECRET_KEY` MUST be set in `.env` - raises `ValueError` if missing
- `ALLOWED_HOSTS` parsed from comma-separated env variable