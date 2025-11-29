# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LCAI Maths is a Django-based web application providing an AI-powered interactive tutor for Leaving Certificate Honours Maths students. The system combines question-based learning with OpenAI integration for grading, hints, and contextual help.

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
source venv/bin/activate  # or source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Load environment variables from .env (already handled in settings.py)
# Required: OPENAI_API_KEY, OPENAI_ORG_ID, OPENAI_EMBED_MODEL, OPENAI_CHAT_MODEL, FAQ_MATCH_THRESHOLD
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

### Database
- MySQL connection: `lcaim` database on localhost:3306
- Username: `morgan`, Password: `help1234`
- Access via Django ORM or direct MySQL client

### Testing Notes
- Note embeddings regenerate on save if title/topic/metadata changes
- Test grading logic in `interactive_lessons/stats_tutor.py` for numeric/algebraic answers
- InfoBot queries logged in `InfoBotQuery` model for review

## URL Structure

- `/` - Home (home app)
- `/admin/` - Django admin
- `/students/` - Student dashboard, login, progress
- `/interactive/` - Question interface, topics
  - `/interactive/<topic-slug>/exam-questions/` - Exam questions for a topic (practice mode)
- `/exam-papers/` - Exam papers list and timed exams
- `/notes/` - Notes management
- `/chat/` - AI chat interface
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