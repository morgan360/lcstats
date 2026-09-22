"""Tunables for study plans, gathered so tuning is a one-line diff.

The numbers here are judgement calls, not measurements. They were chosen to be
defensible to a teacher rather than optimal, and they are expected to move once
real plans have run for a term.
"""

# --- Badge Tests (StudyPlanCheckpoint) -------------------------------------------------------

#: Exam parts in a Badge Test, when the teacher does not say otherwise.
DEFAULT_CHECKPOINT_SIZE = 3

#: Extra rounds of Badge Test parts held back at build time, so a student who
#: fails twice still meets parts they have never seen.
RETRY_ROUNDS = 2

#: Marks lost for help taken, matching the convention the graders already use
#: (see CLAUDE.md: hint -20%, solution -50%).
HINT_PENALTY = 0.20
SOLUTION_PENALTY = 0.50

# --- Plan shape ------------------------------------------------------------

DEFAULT_WEEKLY_MINUTES = 120
DEFAULT_TARGET_MASTERY = 75

# --- Completion thresholds -------------------------------------------------

EXAM_PART_DONE_RATIO = 0.5
EXAM_QUESTION_DONE_RATIO = 0.6
SECTION_DONE_RATIO = 0.7
SECTION_DONE_MEAN_SCORE = 50
FLASHCARD_DONE_RATIO = 0.8
QUICKKICK_DONE_SCORE = 50

# --- Nightly run -----------------------------------------------------------

#: Items in the retry MicroBadge a failed Badge Test adds.
MAX_REVISITS_PER_RETRY = 2

#: How stale a plan's progress may be before the student's own page refreshes it.
REFRESH_THROTTLE_MINUTES = 15

# --- MicroBadges ------------------------------------------------------------

#: MicroBadges per topic. Earning every one opens the Badge Test.
MICROBADGES_PER_TOPIC = 10

#: Days between the last MicroBadge's target date and the deadline, left for
#: sitting the Badge Test.
BADGE_TEST_BUFFER_DAYS = 7

#: Days to earn a retry MicroBadge after a failed Badge Test.
RETRY_MICROBADGE_DAYS = 7

#: Days a MicroBadge may run past its target before the teacher is told.
BEHIND_FLAG_DAYS = 14
