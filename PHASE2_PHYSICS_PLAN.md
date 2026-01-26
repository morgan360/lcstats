# Phase 2: Physics App Implementation Plan

**Created:** 2026-01-26
**Strategy:** Two-phase approach - Quick Demo → Polished Product

---

## Phase 2A: Quick Demo (6-8 Weeks)
**Goal:** Functional Physics app using existing infrastructure for demo purposes

### Week 1-2: Multi-Subject Architecture
- [ ] Create `Subject` model in new `core` app
- [ ] Add migrations for Subject (seed with Maths, Physics)
- [ ] Add `subject` ForeignKey to Topic model
- [ ] Add `subject` ForeignKey to ExamPaper model
- [ ] Update admin to show subject filters
- [ ] Create homepage subject selector (Maths/Physics cards)
- [ ] Add subject context to session/middleware
- [ ] Filter all dashboard queries by current subject

**Key Files:**
- `core/models.py` (new)
- `interactive_lessons/models.py`
- `exam_papers/models.py`
- `home/templates/home/index.html`

### Week 3-4: Physics Content Setup (Reuse Existing Systems!)
- [ ] **Grading:** Confirm `stats_tutor.py` GPT grading works for physics
- [ ] Test unit answers: "9.8 m/s²", "50 N", "100 J"
- [ ] **Diagrams:** Use existing `QuestionPart.image` field
- [ ] Upload test circuit diagram, ray diagram, force diagram
- [ ] **QuickKicks:** Embed PhET using existing `geogebra_code` pattern
- [ ] Test PhET iframe: `https://phet.colorado.edu/sims/html/[simulation]/latest/[simulation]_en.html`
- [ ] Create 10 physics topics via Django admin

**Key Insight:** NO new grading code needed - GPT handles physics answers!

### Week 5-6: Content Creation
- [ ] Write 50 physics questions (5 per topic)
- [ ] Upload diagrams for each question
- [ ] Add correct answers and marking schemes
- [ ] Create 10 PhET simulation QuickKicks
- [ ] Create 5 flashcard sets (10 cards each)
- [ ] Add 5 physics exam papers (past LC papers)

**Content Sources:**
- Leaving Cert Physics past papers (2015-2024)
- Physics textbooks for question ideas
- PhET simulations catalog: https://phet.colorado.edu/

### Week 7-8: Testing & Demo Prep
- [ ] Beta test with 5-10 students
- [ ] Fix any grading issues
- [ ] Polish UI/UX issues
- [ ] Test subject switching
- [ ] Demo presentation ready

**Demo Deliverable:** Working Physics app with 50 questions

---

## Phase 2B: Polished Version (3-4 Months Later)
**Goal:** Production-ready with custom physics features

### Month 1: Advanced Physics Grading
- [ ] Create `interactive_lessons/physics_tutor.py`
- [ ] Install `pint` library for unit validation
- [ ] Normalize units: m/s² ↔ m·s⁻², N ↔ kg·m/s²
- [ ] Implement partial credit for correct method
- [ ] Physics-specific GPT prompts for conceptual answers
- [ ] Add vector answer support (magnitude + direction)

**Technical:**
```python
from pint import UnitRegistry
ureg = UnitRegistry()

def normalize_physics_answer(answer_str):
    # "9.8 m/s²" → Quantity(9.8, m/s²)
    # Compare in normalized SI units
```

### Month 2: Enhanced Diagrams
- [ ] Add `QuestionDiagram` model (M2M with QuestionPart)
- [ ] Multi-image upload per question
- [ ] Diagram labeling/annotation system
- [ ] Export templates for CircuitLab, Inkscape
- [ ] Image zoom/viewer component

### Month 3: Advanced Features
- [ ] PhET simulation catalog in admin
- [ ] Subject-specific analytics dashboard
- [ ] Progress heatmaps per topic
- [ ] Teacher class subject filtering
- [ ] Enhanced reporting per subject

### Month 4: Content Expansion + Payment
- [ ] Expand to 200+ physics questions
- [ ] Add all LC Physics exam papers (2010-2024)
- [ ] Stripe payment integration
- [ ] `SubjectEnrollment` model
- [ ] Per-subject subscription (€15/month per subject)
- [ ] Bundle discount (€25/month both subjects)
- [ ] Launch marketing campaign

---

## Architecture Decisions

### Multi-Subject Model
```python
# core/models.py
class Subject(models.Model):
    name = models.CharField(max_length=50)  # "Maths", "Physics"
    slug = models.SlugField(unique=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['display_order']
```

### Model Updates (Phase 2A)
```python
# interactive_lessons/models.py
class Topic(models.Model):
    subject = models.ForeignKey('core.Subject', on_delete=models.CASCADE)
    # ... existing fields

# exam_papers/models.py
class ExamPaper(models.Model):
    subject = models.ForeignKey('core.Subject', on_delete=models.CASCADE)
    # ... existing fields
```

### Homepage Subject Selector (Phase 2A)
- Side-by-side cards: "Maths" | "Physics"
- Store choice in session: `request.session['current_subject'] = 'maths'`
- Middleware adds subject to context
- All queries filter by subject

---

## What Works Immediately (No Code Changes!)

| System | Works for Physics? | Notes |
|--------|-------------------|-------|
| Exam Papers | ✅ Yes | Add `subject` FK only |
| Flashcards | ✅ Yes | Reuse entirely |
| Homework | ✅ Yes | Already links to Topics |
| Student Progress | ✅ Yes | Filter by subject |
| Notes/RAG | ✅ Yes | Add physics notes content |
| Grading (GPT) | ✅ Yes | Already handles units! |
| QuickKicks | ✅ Yes | Embed PhET like GeoGebra |

---

## Payment Model (Phase 2B)

### Stripe Subscriptions
```python
# students/models.py (Phase 2B)
class SubjectEnrollment(models.Model):
    student = models.ForeignKey(StudentProfile)
    subject = models.ForeignKey('core.Subject')
    enrollment_type = models.CharField(
        choices=[('trial', 'Free Trial'), ('paid', 'Paid'), ('free', 'Free Access')]
    )
    expires_at = models.DateTimeField(null=True)
    stripe_subscription_id = models.CharField(max_length=100, blank=True)
```

### Pricing Tiers
- **Free Trial:** 7 days per subject
- **Single Subject:** €15/month (Maths OR Physics)
- **Bundle:** €25/month (both subjects, save €5)
- **Annual:** €150/year single, €250/year both (2 months free)

### Middleware Check
```python
# Check enrollment before accessing subject content
if not request.user.has_subject_access(current_subject):
    return redirect('payment_required')
```

---

## Risk Mitigation

| Risk | Phase 2A Mitigation | Phase 2B Mitigation |
|------|-------------------|---------------------|
| Grading accuracy | Use GPT for everything | Custom unit parser |
| Solo dev burnout | Launch with 50 questions only | Hire content creator |
| PhET integration | Manual iframe embed | Build catalog system |
| Student adoption | Free beta for 10 students | Marketing campaign |

---

## Success Metrics

### Phase 2A (Demo) - Week 8
- [ ] Subject selector works on homepage
- [ ] 50 physics questions created
- [ ] 10 students complete 5 questions each
- [ ] Grading accuracy >70% (GPT baseline)
- [ ] 5 PhET simulations embedded

### Phase 2B (Production) - Month 4
- [ ] 200+ physics questions
- [ ] Grading accuracy >90% (custom physics_tutor)
- [ ] 100 paying students across both subjects
- [ ] €2,000 MRR from subscriptions
- [ ] 20 teacher accounts managing classes

---

## Development Workflow

### Phase 2A: Week-by-Week
1. **Week 1:** Subject model + migrations + admin
2. **Week 2:** Homepage selector + filtering
3. **Week 3:** Test grading/diagrams with physics content
4. **Week 4:** Create 10 topics in admin
5. **Week 5:** Write 25 questions
6. **Week 6:** Write 25 more questions + flashcards
7. **Week 7:** Beta testing
8. **Week 8:** Bug fixes + demo prep

### Git Strategy
- `main` branch: Production (Maths only)
- `feature/physics-mvp` branch: Phase 2A work
- `feature/physics-polish` branch: Phase 2B work
- Merge to `main` only after beta testing

---

## Next Actions

### Immediate (This Week)
1. Create `core` Django app
2. Create Subject model
3. Make migrations
4. Seed Maths/Physics subjects
5. Add subject FK to Topic model

### Questions to Resolve
- [ ] Should we support other subjects later? (Chemistry, Biology?)
- [ ] Free tier: How many questions before paywall?
- [ ] Teacher pricing: Free or discounted?
- [ ] Content licensing: Can we use LC past papers legally?

---

## Resources

### Physics Content
- **Exam Papers:** SEC.ie (State Examinations Commission)
- **PhET Simulations:** https://phet.colorado.edu/
- **Diagrams:** Inkscape (free), CircuitLab (freemium)

### Technical Libraries
- **Phase 2A:** No new dependencies!
- **Phase 2B:** `pint` (unit validation), `Pillow` (image processing)

### Reference
- Django Multi-tenancy patterns (for subject filtering)
- Stripe Subscriptions docs
- PhET Embedding guide

---

**Last Updated:** 2026-01-26
**Status:** Approved - Ready to start Phase 2A Week 1
