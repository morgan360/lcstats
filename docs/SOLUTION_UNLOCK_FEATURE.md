# Solution Unlock Feature - Implementation Summary

## Overview

Added solution unlock threshold feature to interactive lessons, matching the existing functionality in exam questions. Solutions now require students to make **2 attempts** (configurable) before becoming visible, or until they get the correct answer.

## Changes Made

### 1. Database Model (`interactive_lessons/models.py`)

Added `solution_unlock_after_attempts` field to `QuestionPart` model:

```python
solution_unlock_after_attempts = models.PositiveIntegerField(
    default=2,
    help_text="Number of attempts before solution becomes visible (0 = always visible, 2 = default for production)"
)
```

**Location:** Line 189-193 in `interactive_lessons/models.py`

### 2. Migration

Created migration `0024_add_solution_unlock_threshold.py`:
- Adds the new field to existing `QuestionPart` records
- Sets default value of `2` for all existing questions
- Migration ran successfully

### 3. View Logic (`interactive_lessons/views.py`)

Updated `section_question_view()` function to:
- Count attempts per question part for the current student
- Determine if solution is unlocked based on three criteria:
  1. Threshold is 0 (always visible), OR
  2. Student has a correct answer, OR
  3. Attempt count >= threshold

**Location:** Lines 424-448 in `interactive_lessons/views.py`

```python
# Check solution unlock status for each part
part_attempt_counts = {}
part_solution_unlocked = {}
for part in parts:
    attempt_count = QuestionAttempt.objects.filter(
        student=request.user.studentprofile,
        question_part=part
    ).count()
    part_attempt_counts[part.id] = attempt_count

    # Solution is unlocked if:
    # 1. Threshold is 0 (always visible), OR
    # 2. Student has correct answer, OR
    # 3. Attempt count >= threshold
    has_correct = QuestionAttempt.objects.filter(
        student=request.user.studentprofile,
        question_part=part,
        is_correct=True
    ).exists()

    part_solution_unlocked[part.id] = (
        part.solution_unlock_after_attempts == 0 or
        has_correct or
        attempt_count >= part.solution_unlock_after_attempts
    )
```

Context variables passed to template:
- `part_attempt_counts` - Dictionary of part_id → attempt count
- `part_solution_unlocked` - Dictionary of part_id → boolean (is unlocked)

### 4. Template Updates (`interactive_lessons/templates/interactive_lessons/quiz.html`)

**Added conditional solution display:**
- Solutions shown only if `part_solution_unlocked[part.id]` is True
- Shows "Solution Locked" message if not unlocked
- Displays current attempt count and threshold required

**Location:** Lines 84-117 in `quiz.html`

```django
{% if part_solution_unlocked and part.id in part_solution_unlocked and part_solution_unlocked|get_item:part.id %}
    <!-- Show solution -->
    <details class="mt-4 rounded-md border border-[#a5d6a7] bg-[#e8f5e9]...">
        <summary>📝 Solution for {{ part.label }}</summary>
        ...
    </details>
{% else %}
    <!-- Show locked message -->
    <div class="mt-4 rounded-md border border-[#ffc107] bg-[#fff3cd]...">
        <div class="font-semibold text-[#856404]">🔒 Solution Locked</div>
        <div class="mt-2 text-sm text-[#856404]">
            You have made {{ part_attempt_counts|get_item:part.id }} attempt(s).
            Solution unlocks after {{ part.solution_unlock_after_attempts }} attempt(s) or when you get the correct answer.
        </div>
    </div>
{% endif %}
```

### 5. Template Filter (`interactive_lessons/templatetags/dict_filters.py`)

Created custom template filter `get_item` to access dictionary values in templates:

```python
@register.filter
def get_item(dictionary, key):
    """
    Template filter to get an item from a dictionary.
    Usage: {{ my_dict|get_item:my_key }}
    """
    if dictionary is None:
        return None
    return dictionary.get(key)
```

**Template usage:** `{% load dict_filters %}` at the top of `quiz.html`

## Configuration Options

### Per-Question Configuration (Django Admin)

Teachers/admins can customize the unlock threshold per question part:

1. Go to **Admin → Interactive Lessons → Question Parts**
2. Edit any question part
3. Set **"Solution unlock after attempts"** field:
   - `0` = Solution always visible (no lock)
   - `1` = Unlocks after 1 attempt
   - `2` = Unlocks after 2 attempts (default)
   - `3+` = Higher thresholds for more challenging questions

### Default for Production

All new `QuestionPart` records will have `solution_unlock_after_attempts = 2` by default.

### Unlock Conditions

Solution unlocks when **ANY** of these conditions are met:
1. **Threshold is 0** - Always visible
2. **Student gets correct answer** - Instant unlock
3. **Attempt count >= threshold** - After enough tries

## User Experience

### Before Unlock (< 2 attempts, no correct answer)
Students see:
```
🔒 Solution Locked
You have made 1 attempt.
Solution unlocks after 2 attempts or when you get the correct answer.
```

### After Unlock (≥ 2 attempts OR correct answer)
Students see:
```
📝 Solution for (a) [clickable details dropdown]
[Full solution content with LaTeX and images]
```

## Consistency with Exam Questions

This implementation mirrors the existing exam questions feature:
- `ExamQuestionPart.solution_unlock_after_attempts` (default: 2)
- Same unlock logic (threshold = 0, correct answer, or attempt count)
- Same user experience with locked/unlocked states

## Testing Checklist

- [x] Migration runs successfully
- [x] Default value of 2 applied to new questions
- [x] Solutions hidden when attempts < 2
- [x] Solutions shown after 2 attempts
- [x] Solutions shown immediately when student gets correct answer
- [x] Solutions always shown when threshold = 0
- [x] Attempt count displays correctly
- [x] Template filter works for dictionary access
- [ ] Test on production site (www.numscoil.ie)

## Deployment Steps

1. **Local (Already Done):**
   - ✅ Model changes committed
   - ✅ Migration created and run locally
   - ✅ View logic updated
   - ✅ Template updated
   - ✅ Template filter created

2. **Production Deployment:**
   ```bash
   # On production server
   cd ~/lcstats
   source venv/bin/activate
   git pull origin main
   python manage.py migrate interactive_lessons
   touch /var/www/morgan360_pythonanywhere_com_wsgi.py
   ```

3. **Verification:**
   - Test with a student account
   - Attempt a question once - solution should be locked
   - Attempt same question twice - solution should unlock
   - Get correct answer on first try - solution should unlock immediately

## Backward Compatibility

- ✅ All existing questions will have threshold = 2 (migration sets default)
- ✅ No breaking changes to existing functionality
- ✅ Teachers can adjust thresholds per question via admin
- ✅ Setting threshold to 0 restores old "always visible" behavior

## Future Enhancements (Optional)

1. **Bulk Update Tool:** Admin action to set threshold for multiple questions at once
2. **Per-Topic Defaults:** Set default threshold per topic
3. **Analytics:** Track how often students view solutions vs. solving independently
4. **Hints Integration:** Different thresholds for hints vs. full solutions

---

**Implemented:** January 2026
**Status:** Ready for production deployment
**Production URL:** https://www.numscoil.ie