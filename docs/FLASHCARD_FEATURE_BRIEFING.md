# Flashcard System Feature - Developer Briefing

**Project:** LCAI Maths (Leaving Certificate Maths Interactive Tutor)
**Repository:** https://github.com/morgan360/lcstats.git
**Feature:** Topic-based Flashcard System with Self-Assessment & Spaced Repetition
**Target App:** New Django app (`flashcards/`) within existing project

---

## 🎯 Feature Overview

Build a flashcard study system where students can:
1. **Study flashcards** for key definitions, formulas, and theorems per topic
2. **Self-assess** each card by checking "I know this"
3. **Take a multiple-choice quiz** after studying to test retention
4. **Track mastery** with spaced repetition algorithm (show difficult cards more frequently)

---

## 🚀 Getting Started

### Prerequisites
- **Python 3.12+** (project uses 3.12.11)
- **MySQL** database server
- **Git** installed
- **Claude Code account** (see setup below)
- **OpenAI API key** (for AI features)

### 1. Clone the Repository

```bash
git clone https://github.com/morgan360/lcstats.git
cd lcstats
```

### 2. Set Up Python Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate  # On macOS/Linux
# OR
venv\Scripts\activate     # On Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

**Key dependencies you'll be working with:**
- Django 5.2.7
- MySQL client (mysqlclient 2.2.7)
- OpenAI API (openai 2.1.0)
- LangChain (for RAG features)

### 4. Configure Environment Variables

Create a `.env` file in the project root:

```bash
# .env file
DEBUG=True
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DB_NAME=lcaim
DB_USER=morgan
DB_PASSWORD=help1234
DB_HOST=localhost
DB_PORT=3306

# OpenAI (required for AI grading/chat features)
OPENAI_API_KEY=your-openai-api-key
OPENAI_ORG_ID=your-org-id
OPENAI_EMBED_MODEL=text-embedding-3-small
OPENAI_CHAT_MODEL=gpt-4o-mini
FAQ_MATCH_THRESHOLD=0.7
```

**Note:** Request OpenAI credentials from project owner if needed for development.

### 5. Set Up MySQL Database

```bash
# Connect to MySQL
mysql -u root -p

# Create database
CREATE DATABASE lcaim CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

# Create user (if not exists)
CREATE USER 'morgan'@'localhost' IDENTIFIED BY 'help1234';
GRANT ALL PRIVILEGES ON lcaim.* TO 'morgan'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

### 6. Run Migrations

```bash
python manage.py migrate
```

### 7. Create Superuser (for Django Admin)

```bash
python manage.py createsuperuser
```

### 8. Run Development Server

```bash
python manage.py runserver
```

Visit: http://127.0.0.1:8000/admin/

---

## 🤖 Setting Up Claude Code

### What is Claude Code?
Claude Code is an AI-powered CLI tool that helps with software development tasks. It can read code, make edits, run tests, and assist with implementation.

### Installation

1. **Sign up for Claude account:**
   - Visit https://claude.ai/code
   - Create an account if you don't have one

2. **Install Claude Code CLI:**
   ```bash
   # macOS/Linux
   curl https://install.claude.ai/code | bash

   # Or via npm
   npm install -g @anthropic/claude-code
   ```

3. **Authenticate:**
   ```bash
   claude login
   ```

4. **Navigate to project:**
   ```bash
   cd /path/to/lcstats
   ```

5. **Start Claude Code:**
   ```bash
   claude
   ```

### How to Use Claude Code for This Feature

Claude Code can help you:
- Understand existing codebase architecture
- Generate model definitions
- Write views and URL patterns
- Create templates with proper styling
- Debug issues

**Example prompts:**
```
"Show me the structure of the interactive_lessons app"
"Create a Flashcard model linked to Topics"
"Generate a view for displaying flashcard study session"
"Help me implement spaced repetition algorithm"
```

---

## 📋 Feature Requirements

### User Flow

1. **Topic Selection** → Student clicks "Study Flashcards" button on topic page
2. **Study Session** → Cards displayed one at a time:
   - Show card front (question/prompt)
   - Student clicks to reveal back (answer)
   - Student checks "I know this" or leaves unchecked for "Don't know"
   - Next card shown
3. **Quiz Time** → After reviewing all cards:
   - Multiple choice quiz (10-15 questions)
   - Mix of cards marked "know" and "don't know"
   - Auto-graded
4. **Results & SRS Update** →
   - Show quiz score
   - Update spaced repetition schedule
   - Show next review date

### Content Structure

**Flashcard types:**
- **Definition** (e.g., "What is a function?" → "A relation where each input has exactly one output")
- **Formula** (e.g., "Area of circle?" → "πr²")
- **Theorem** (e.g., "Pythagoras?" → "a² + b² = c²")
- **Concept** (e.g., "What is standard deviation?" → "Measure of spread...")

---

## 🗄️ Database Models

### Create new app: `flashcards/`

```bash
python manage.py startapp flashcards
```

Add to `INSTALLED_APPS` in `lcstats/settings.py`:
```python
INSTALLED_APPS = [
    # ... existing apps ...
    'flashcards',
]
```

### Model Definitions

**File:** `flashcards/models.py`

```python
from django.db import models
from django.utils import timezone
from interactive_lessons.models import Topic, Section
from students.models import StudentProfile

class Flashcard(models.Model):
    """Individual flashcard with front/back content"""

    DIFFICULTY_CHOICES = [
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard'),
    ]

    TYPE_CHOICES = [
        ('definition', 'Definition'),
        ('formula', 'Formula'),
        ('theorem', 'Theorem'),
        ('concept', 'Concept'),
    ]

    topic = models.ForeignKey(
        Topic,
        on_delete=models.CASCADE,
        related_name='flashcards'
    )
    section = models.ForeignKey(
        Section,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='flashcards'
    )

    # Card content
    front_text = models.TextField(help_text="Question/prompt (supports LaTeX)")
    back_text = models.TextField(help_text="Answer/definition (supports LaTeX)")
    hint = models.TextField(blank=True, null=True, help_text="Optional hint")

    # Metadata
    card_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='definition')
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default='medium')
    order = models.PositiveIntegerField(default=0, help_text="Display order within topic")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['topic', 'order']
        unique_together = ['topic', 'order']

    def __str__(self):
        return f"{self.topic.name} - {self.front_text[:50]}"


class FlashcardAttempt(models.Model):
    """Tracks student interactions with individual flashcards (for SRS)"""

    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name='flashcard_attempts'
    )
    flashcard = models.ForeignKey(
        Flashcard,
        on_delete=models.CASCADE,
        related_name='attempts'
    )

    # Self-assessment
    knew_it = models.BooleanField(
        default=False,
        help_text="Did student mark 'I know this'?"
    )

    # Spaced Repetition System (SM-2 algorithm)
    repetition_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of times reviewed"
    )
    ease_factor = models.FloatField(
        default=2.5,
        help_text="Difficulty multiplier (1.3-2.5)"
    )
    interval_days = models.PositiveIntegerField(
        default=1,
        help_text="Days until next review"
    )
    next_review_date = models.DateField(
        default=timezone.now,
        help_text="When to show this card again"
    )

    attempted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-attempted_at']
        unique_together = ['student', 'flashcard']

    def __str__(self):
        status = "✓" if self.knew_it else "✗"
        return f"{self.student.user.username} - {self.flashcard} ({status})"

    def update_srs(self, quiz_correct=None):
        """
        Update spaced repetition parameters based on performance.

        Args:
            quiz_correct (bool): Did student answer correctly in quiz?
                                If None, use self-assessment only.
        """
        self.repetition_count += 1

        # Determine quality of recall (0-5 scale)
        if quiz_correct is False:
            quality = 0  # Failed quiz
        elif quiz_correct is True:
            quality = 4 if self.knew_it else 3  # Passed quiz
        else:
            quality = 3 if self.knew_it else 2  # Self-assessment only

        # SM-2 Algorithm
        if quality < 3:
            # Failed - reset interval
            self.repetition_count = 0
            self.interval_days = 1
        else:
            # Passed - increase interval
            if self.repetition_count == 1:
                self.interval_days = 1
            elif self.repetition_count == 2:
                self.interval_days = 6
            else:
                self.interval_days = int(self.interval_days * self.ease_factor)

        # Update ease factor
        self.ease_factor = max(1.3, self.ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)))

        # Set next review date
        self.next_review_date = timezone.now().date() + timezone.timedelta(days=self.interval_days)
        self.save()


class FlashcardSession(models.Model):
    """Tracks a complete study session for a topic"""

    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name='flashcard_sessions'
    )
    topic = models.ForeignKey(
        Topic,
        on_delete=models.CASCADE,
        related_name='flashcard_sessions'
    )

    # Session timing
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Study phase stats
    cards_reviewed = models.PositiveIntegerField(default=0)
    cards_known = models.PositiveIntegerField(default=0)

    # Quiz phase stats
    quiz_score = models.FloatField(
        null=True,
        blank=True,
        help_text="Quiz score percentage (0-100)"
    )
    quiz_questions = models.PositiveIntegerField(default=0)
    quiz_correct = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-started_at']

    def __str__(self):
        return f"{self.student.user.username} - {self.topic.name} ({self.started_at.date()})"

    @property
    def is_completed(self):
        return self.completed_at is not None

    @property
    def knowledge_rate(self):
        """Percentage of cards marked as known"""
        if self.cards_reviewed == 0:
            return 0
        return round((self.cards_known / self.cards_reviewed) * 100, 1)


class QuizQuestion(models.Model):
    """Individual question in a flashcard quiz"""

    session = models.ForeignKey(
        FlashcardSession,
        on_delete=models.CASCADE,
        related_name='quiz_questions'
    )
    flashcard = models.ForeignKey(
        Flashcard,
        on_delete=models.CASCADE
    )

    # Multiple choice options (JSON field would be better, but keeping simple)
    option_a = models.TextField()
    option_b = models.TextField()
    option_c = models.TextField()
    option_d = models.TextField()
    correct_option = models.CharField(
        max_length=1,
        choices=[('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D')]
    )

    # Student answer
    student_answer = models.CharField(
        max_length=1,
        choices=[('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D')],
        null=True,
        blank=True
    )
    is_correct = models.BooleanField(default=False)

    answered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"Quiz Q: {self.flashcard.front_text[:30]}"
```

---

## 🎨 Views & URLs

### URL Structure

**File:** `flashcards/urls.py`

```python
from django.urls import path
from . import views

app_name = 'flashcards'

urlpatterns = [
    # Topic flashcard overview
    path('<slug:topic_slug>/', views.flashcard_overview, name='overview'),

    # Study session
    path('<slug:topic_slug>/study/', views.study_session, name='study'),
    path('<slug:topic_slug>/study/next/', views.next_card, name='next_card'),
    path('<slug:topic_slug>/study/mark/<int:flashcard_id>/', views.mark_card, name='mark_card'),

    # Quiz
    path('<slug:topic_slug>/quiz/', views.start_quiz, name='start_quiz'),
    path('<slug:topic_slug>/quiz/submit/', views.submit_quiz, name='submit_quiz'),

    # Results
    path('session/<int:session_id>/results/', views.session_results, name='results'),
]
```

### Key Views to Implement

**File:** `flashcards/views.py`

1. **`flashcard_overview(request, topic_slug)`**
   - Show all flashcards for topic
   - Display mastery stats (X/Y cards mastered)
   - "Start Study Session" button
   - Show last session results

2. **`study_session(request, topic_slug)`**
   - Create new FlashcardSession
   - Use SRS to prioritize cards due for review
   - Show first card with flip animation
   - Track "I know this" checkboxes

3. **`next_card(request, topic_slug)` (AJAX)**
   - Return next card in JSON
   - Update session progress
   - Check if study phase complete → redirect to quiz

4. **`start_quiz(request, topic_slug)`**
   - Generate 10-15 multiple choice questions
   - Mix of known/unknown cards from session
   - Create QuizQuestion objects
   - Render quiz template

5. **`submit_quiz(request, topic_slug)` (POST)**
   - Grade quiz answers
   - Update FlashcardAttempt records (call `update_srs()`)
   - Calculate session stats
   - Mark session as completed
   - Redirect to results

6. **`session_results(request, session_id)`**
   - Display quiz score
   - Show which questions were correct/incorrect
   - Display next review dates for each card
   - "Study Again" button

---

## 🎨 Frontend Templates

### Base Template Structure

Create templates in `flashcards/templates/flashcards/`:

1. **`overview.html`** - Topic flashcard dashboard
2. **`study.html`** - Study session interface (card flip UI)
3. **`quiz.html`** - Multiple choice quiz
4. **`results.html`** - Session results

### Example: Card Flip CSS

```css
.flashcard {
    width: 600px;
    height: 400px;
    perspective: 1000px;
    margin: 2rem auto;
}

.flashcard-inner {
    position: relative;
    width: 100%;
    height: 100%;
    transition: transform 0.6s;
    transform-style: preserve-3d;
}

.flashcard.flipped .flashcard-inner {
    transform: rotateY(180deg);
}

.flashcard-front, .flashcard-back {
    position: absolute;
    width: 100%;
    height: 100%;
    backface-visibility: hidden;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 2rem;
    background: white;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}

.flashcard-back {
    transform: rotateY(180deg);
}
```

### JavaScript for Card Flip

```javascript
document.querySelector('.flashcard').addEventListener('click', function() {
    this.classList.toggle('flipped');
});
```

---

## 🧮 Spaced Repetition Algorithm

Implement **SM-2 (SuperMemo 2)** algorithm in `FlashcardAttempt.update_srs()`:

### Algorithm Summary

1. **Quality of recall** (0-5):
   - 0: Complete blackout
   - 3: Correct response with effort
   - 4: Correct response after hesitation
   - 5: Perfect response

2. **Interval calculation**:
   - First repetition: 1 day
   - Second repetition: 6 days
   - Subsequent: interval × ease_factor

3. **Ease factor update**:
   ```
   EF' = EF + (0.1 - (5 - quality) × (0.08 + (5 - quality) × 0.02))
   Minimum EF = 1.3
   ```

4. **Failure handling**:
   - If quality < 3: reset repetition count, interval = 1 day

---

## 🔗 Integration Points

### 1. Add to Topic Selection Page

**File:** `interactive_lessons/templates/interactive_lessons/select_topic.html`

Add button after "Start Practice":

```html
<a href="{% url 'flashcards:overview' topic.slug %}"
   class="btn btn-primary">
   📚 Study Flashcards
</a>
```

### 2. Update Student Dashboard

**File:** `students/templates/students/dashboard.html`

Add flashcard stats:

```html
<div class="stat-card">
    <p>Flashcards Mastered</p>
    <p class="stat-value">{{ flashcards_mastered }}</p>
</div>
```

**Update:** `students/views.py` → `dashboard` view to include:

```python
from flashcards.models import FlashcardAttempt

def dashboard(request):
    # ... existing code ...

    flashcards_mastered = FlashcardAttempt.objects.filter(
        student=profile,
        repetition_count__gte=3,
        ease_factor__gte=2.0
    ).count()

    context['flashcards_mastered'] = flashcards_mastered
```

### 3. Admin Interface

**File:** `flashcards/admin.py`

```python
from django.contrib import admin
from .models import Flashcard, FlashcardAttempt, FlashcardSession, QuizQuestion

@admin.register(Flashcard)
class FlashcardAdmin(admin.ModelAdmin):
    list_display = ['topic', 'front_text_short', 'card_type', 'difficulty', 'order']
    list_filter = ['topic', 'card_type', 'difficulty']
    search_fields = ['front_text', 'back_text']
    ordering = ['topic', 'order']

    def front_text_short(self, obj):
        return obj.front_text[:50]
    front_text_short.short_description = 'Front Text'

@admin.register(FlashcardSession)
class FlashcardSessionAdmin(admin.ModelAdmin):
    list_display = ['student', 'topic', 'started_at', 'quiz_score', 'knowledge_rate']
    list_filter = ['topic', 'started_at']
    readonly_fields = ['started_at', 'completed_at']
```

---

## 📝 Git Workflow & Pull Requests

### Create Feature Branch

```bash
# Make sure you're on main and up to date
git checkout main
git pull origin main

# Create feature branch
git checkout -b feature/flashcard-system
```

### Development Cycle

```bash
# Make changes to files...

# Check what changed
git status
git diff

# Stage changes
git add flashcards/
git add interactive_lessons/templates/  # if you modified templates

# Commit with descriptive message
git commit -m "Add Flashcard models and SRS algorithm

- Created Flashcard, FlashcardAttempt, FlashcardSession models
- Implemented SM-2 spaced repetition algorithm
- Added admin interface for flashcard management"

# Push to GitHub
git push origin feature/flashcard-system
```

### Submit Pull Request

1. **Go to GitHub:** https://github.com/morgan360/lcstats
2. **Click "Compare & pull request"** button (appears after push)
3. **Fill in PR details:**

**Title:** `Feature: Flashcard System with Spaced Repetition`

**Description:**
```markdown
## Summary
Implements a complete flashcard study system for topic-based learning.

## Changes
- ✅ New `flashcards` Django app
- ✅ Models: Flashcard, FlashcardAttempt, FlashcardSession, QuizQuestion
- ✅ SM-2 spaced repetition algorithm
- ✅ Study session views with card flip UI
- ✅ Multiple choice quiz generation
- ✅ Integration with student dashboard and topic selection
- ✅ Admin interface for managing flashcards

## Testing
- [ ] Create flashcards via admin
- [ ] Study session flow works correctly
- [ ] Self-assessment checkboxes track properly
- [ ] Quiz generates correct multiple choice questions
- [ ] SRS intervals update after quiz
- [ ] Session results display correctly

## Screenshots
[Add screenshots if applicable]

## Related Issues
Closes #[issue number if applicable]
```

4. **Request review** from project owner
5. **Address review comments** if needed:
   ```bash
   # Make requested changes
   git add .
   git commit -m "Address PR feedback: fix quiz grading logic"
   git push origin feature/flashcard-system
   ```

### After PR is Merged

```bash
# Switch back to main
git checkout main

# Pull latest changes (including your merged PR)
git pull origin main

# Delete feature branch (cleanup)
git branch -d feature/flashcard-system
```

---

## 🧪 Testing Checklist

### Manual Testing Steps

1. **Admin Setup:**
   - [ ] Create 10-15 flashcards for a topic (mix of types)
   - [ ] Verify LaTeX rendering in admin preview
   - [ ] Check ordering works

2. **Study Session:**
   - [ ] Start session from topic page
   - [ ] Card flip animation works
   - [ ] "I know this" checkbox saves state
   - [ ] Progress bar updates
   - [ ] All cards shown before quiz

3. **Quiz:**
   - [ ] 10-15 questions generated
   - [ ] Multiple choice options are randomized
   - [ ] Correct answer is actually correct
   - [ ] Submit button works
   - [ ] Score calculated correctly

4. **SRS Behavior:**
   - [ ] "Don't know" cards → next_review_date = tomorrow
   - [ ] "Know" cards → next_review_date = 6+ days
   - [ ] Failed quiz question → interval resets to 1 day
   - [ ] Passed quiz question → interval increases

5. **Dashboard Integration:**
   - [ ] Flashcard stats show on student dashboard
   - [ ] Recent sessions appear
   - [ ] "Study Flashcards" button visible on topics

### Database Checks

```bash
python manage.py shell
```

```python
from flashcards.models import Flashcard, FlashcardAttempt, FlashcardSession
from students.models import StudentProfile

# Check flashcards created
Flashcard.objects.all().count()

# Check student attempts
profile = StudentProfile.objects.first()
FlashcardAttempt.objects.filter(student=profile)

# Check SRS intervals
for attempt in FlashcardAttempt.objects.filter(student=profile):
    print(f"{attempt.flashcard.front_text[:30]} - Next: {attempt.next_review_date}")
```

---

## 📚 Resources & Documentation

### Project Documentation
- **Main README:** `/README.md`
- **Claude.md:** `/CLAUDE.md` (architecture overview)
- **Database sync:** `/docs/DATABASE_SYNC_MANUAL.md`

### Django Resources
- Django 5.2 Docs: https://docs.djangoproject.com/en/5.2/
- Model Field Reference: https://docs.djangoproject.com/en/5.2/ref/models/fields/
- Views & URLs: https://docs.djangoproject.com/en/5.2/topics/http/views/

### Spaced Repetition
- SM-2 Algorithm: https://www.supermemo.com/en/archives1990-2015/english/ol/sm2
- Anki Documentation: https://docs.ankiweb.net/studying.html

### Frontend
- Bootstrap 5: https://getbootstrap.com/docs/5.0/
- KaTeX (LaTeX): https://katex.org/docs/api.html

---

## 🐛 Common Issues & Troubleshooting

### MySQL Connection Errors
```bash
# Check MySQL is running
mysql -u morgan -p

# If connection refused:
brew services start mysql  # macOS
sudo systemctl start mysql # Linux
```

### Migration Conflicts
```bash
# If migrations conflict:
python manage.py makemigrations --merge
python manage.py migrate
```

### Static Files Not Loading
```bash
# Collect static files
python manage.py collectstatic --noinput

# In development, DEBUG=True should serve static files automatically
```

### OpenAI API Errors
- Verify `.env` has correct `OPENAI_API_KEY`
- Check API quota: https://platform.openai.com/usage
- Flashcard feature doesn't require OpenAI (only used for grading in other features)

---

## 📞 Contact & Support

**Project Owner:** [Add contact info]
**GitHub Issues:** https://github.com/morgan360/lcstats/issues
**Pull Request Reviews:** Tag owner in PR comments

---

## ✅ Deliverables Checklist

Before submitting PR, ensure:

- [ ] Models created and migrated
- [ ] Views implemented and tested
- [ ] Templates created with proper styling
- [ ] URL patterns configured
- [ ] Admin interface functional
- [ ] Integration points updated (dashboard, topic page)
- [ ] SRS algorithm working correctly
- [ ] Code follows Django best practices
- [ ] No hardcoded values (use settings/env vars)
- [ ] LaTeX rendering works in flashcards
- [ ] Responsive design (mobile-friendly)
- [ ] Git commits are clean and descriptive
- [ ] PR description is comprehensive

---

**Good luck! Feel free to use Claude Code throughout development for assistance with implementation details, debugging, and code review.**