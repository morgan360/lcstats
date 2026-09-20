"""Tunables for study plans, gathered so tuning is a one-line diff.

The numbers here are judgement calls, not measurements. They were chosen to be
defensible to a teacher rather than optimal, and they are expected to move once
real plans have run for a term.
"""

# --- Checkpoints -----------------------------------------------------------

#: Exam parts in a checkpoint, when the teacher does not say otherwise.
DEFAULT_CHECKPOINT_SIZE = 3

#: Extra rounds of checkpoint parts held back at build time, so a student who
#: fails twice still meets parts they have never seen.
RETRY_ROUNDS = 2

#: Share of a goal's practice items that must be done before its checkpoint
#: unlocks on its own. A teacher can always unlock early.
CHECKPOINT_UNLOCK_RATIO = 0.8

#: Marks lost for help taken, matching the convention the graders already use
#: (see CLAUDE.md: hint -20%, solution -50%).
HINT_PENALTY = 0.20
SOLUTION_PENALTY = 0.50

# --- Plan shape ------------------------------------------------------------

DEFAULT_WEEKLY_MINUTES = 120
DEFAULT_TARGET_MASTERY = 75

#: A wall of tasks is a worse plan than a short one, whatever the budget allows.
MAX_ITEMS_PER_WEEK = 12

#: Share of each week after the first left unspent, so the nightly run has
#: somewhere to put extra work without blowing the student's time commitment.
REVISIT_RESERVE_RATIO = 0.15

#: How far over a topic's remaining budget the last item may push, rather than
#: leaving a few minutes stranded.
FINAL_ITEM_OVERFLOW = 1.20

# --- Completion thresholds -------------------------------------------------

EXAM_PART_DONE_RATIO = 0.5
EXAM_QUESTION_DONE_RATIO = 0.6
SECTION_DONE_RATIO = 0.7
SECTION_DONE_MEAN_SCORE = 50
FLASHCARD_DONE_RATIO = 0.8
QUICKKICK_DONE_SCORE = 50

# --- Nightly run -----------------------------------------------------------

#: Times an item is rolled into a new week before the teacher is told instead.
MAX_CARRY_OVERS = 3

#: Revisit items added per topic per week after a failed checkpoint.
MAX_REVISITS_PER_TOPIC_PER_WEEK = 2

#: How stale a plan's progress may be before the student's own page refreshes it.
REFRESH_THROTTLE_MINUTES = 15
