"""Turning "get solid on these topics by December" into week-by-week work.

``build_plan`` is pure: it reads the student's history and returns a proposal,
and creates nothing. That is what lets the teacher's preview page and the
persisting step share one code path, and it is what makes the whole thing
testable without a database full of half-made plans.

The order work is handed out in is a teaching judgement, not an optimisation.
Recall material comes early, exam parts come late, and anything the student has
already cracked comes last if at all. Parts held back for a checkpoint never
appear here: a capstone sat on a question they have already worked through with
the marking scheme open proves nothing.
"""
import logging
from dataclasses import dataclass, field
from datetime import date, timedelta

from django.db.models import Count, Q

from exam_papers.models import ExamQuestionAttempt, ExamQuestionPart
from flashcards.models import Flashcard, FlashcardAttempt, FlashcardSet
from interactive_lessons.models import Section
from quickkicks.models import QuickKick, QuickKickView
from students.models import QuestionAttempt

from .. import constants
from . import checkpoints as checkpoint_service
from . import estimates

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# The proposal
# ---------------------------------------------------------------------------

@dataclass
class ProposedItem:
    kind: str
    obj: object
    goal_index: int
    estimated_minutes: int
    instructions: str = ''

    @property
    def sort_key(self):
        return (self.goal_index, -self.estimated_minutes)


@dataclass
class ProposedWeek:
    index: int
    start_date: date
    end_date: date
    minutes_budget: int
    items: list = field(default_factory=list)

    @property
    def minutes_used(self):
        return sum(i.estimated_minutes for i in self.items)


@dataclass
class ProposedGoal:
    topic: object
    target_mastery: int
    priority: int
    checkpoint_size: int
    checkpoint_parts: list = field(default_factory=list)
    reserve_rounds: list = field(default_factory=list)
    pool_available: int = 0

    @property
    def reserved_part_ids(self):
        ids = {p.id for p in self.checkpoint_parts}
        for round_parts in self.reserve_rounds:
            ids |= {p.id for p in round_parts}
        return ids


@dataclass
class ProposedPlan:
    goals: list = field(default_factory=list)
    weeks: list = field(default_factory=list)
    warnings: list = field(default_factory=list)

    @property
    def total_items(self):
        return sum(len(w.items) for w in self.weeks)


# ---------------------------------------------------------------------------
# Weeks
# ---------------------------------------------------------------------------

def build_weeks(start_date, deadline, weekly_minutes):
    """Monday-to-Sunday weeks covering the run, first one pro rata."""
    weeks = []
    monday = start_date - timedelta(days=start_date.weekday())
    index = 1
    while monday <= deadline:
        sunday = monday + timedelta(days=6)
        if index == 1:
            # Only the days actually left in this week are available.
            days = (sunday - start_date).days + 1
            budget = max(15, round(weekly_minutes * days / 7 / 5) * 5)
        else:
            budget = weekly_minutes
        weeks.append(ProposedWeek(
            index=index, start_date=monday, end_date=sunday,
            minutes_budget=budget))
        monday = sunday + timedelta(days=1)
        index += 1
    return weeks


def spendable(week):
    """Minutes a week may spend now, holding some back for the nightly run."""
    if week.index == 1:
        return week.minutes_budget
    return int(week.minutes_budget * (1 - constants.REVISIT_RESERVE_RATIO))


# ---------------------------------------------------------------------------
# What the student has already done
# ---------------------------------------------------------------------------

def _section_progress(student, topics):
    """{section_id: (attempted, total)} across these topics, in two queries."""
    sections = list(
        Section.objects.filter(topic__in=topics)
        .annotate(total=Count('questions', distinct=True))
    )
    if not sections:
        return {}, []
    attempted = (
        QuestionAttempt.objects
        .filter(student__user=student, question__section__in=sections)
        .values('question__section')
        .annotate(done=Count('question', distinct=True))
    )
    done_by_section = {r['question__section']: r['done'] for r in attempted}
    return ({s.id: (done_by_section.get(s.id, 0), s.total) for s in sections},
            sections)


def _flashcard_progress(student, topics):
    """{set_id: (mastered, total)} for published sets on these topics."""
    sets = list(FlashcardSet.objects.filter(topic__in=topics, is_published=True))
    if not sets:
        return {}, []
    totals = dict(
        Flashcard.objects.filter(flashcard_set__in=sets)
        .values_list('flashcard_set')
        .annotate(n=Count('id'))
    )
    mastered = dict(
        FlashcardAttempt.objects
        .filter(student=student, flashcard__flashcard_set__in=sets,
                mastery_level__in=('know', 'retired'))
        .values_list('flashcard__flashcard_set')
        .annotate(n=Count('id'))
    )
    return ({s.id: (mastered.get(s.id, 0), totals.get(s.id, 0)) for s in sets},
            sets)


def _best_part_ratios(student, parts):
    """{part_id: best ratio 0-1} for parts this student has attempted."""
    if not parts:
        return {}
    rows = (ExamQuestionAttempt.objects
            .filter(exam_attempt__student=student,
                    question_part__in=parts)
            .values_list('question_part_id', 'marks_awarded', 'max_marks'))
    best = {}
    for part_id, awarded, max_marks in rows:
        if not max_marks:
            continue
        ratio = max(0.0, min(1.0, (awarded or 0) / max_marks))
        if ratio > best.get(part_id, -1):
            best[part_id] = ratio
    return best


# ---------------------------------------------------------------------------
# Candidates
# ---------------------------------------------------------------------------

#: Base scores. Higher is offered sooner. The ordering is the teaching
#: judgement: meet it, practise it, then prove it on exam questions.
BASE_SCORES = {
    'exam_part_untried': 100,
    'exam_part_weak': 90,
    'section_fresh': 80,
    'section_partial': 70,
    'flashcard': 60,
    'quickkick_question': 50,
    'quickkick': 40,
    'exam_part_cracked': 20,
    'quickkick_seen': 15,
}


@dataclass
class Candidate:
    kind: str
    obj: object
    score: int
    minutes: int
    flavour: str

    def ramped(self, ramp):
        """Exam work is worth more late on; recall work more early on."""
        if self.kind in ('exam_part', 'exam_question'):
            return self.score + 30 * ramp
        if self.kind in ('flashcard', 'quickkick'):
            return self.score - 20 * ramp
        return self.score


def candidates_for_goal(student, topic, excluded_part_ids):
    """Everything this student could usefully do on this topic, best first."""
    out = []

    parts = [p for p in ExamQuestionPart.objects
             .filter(topic=topic, question__exam_paper__is_published=True)
             .select_related('question__exam_paper')
             if p.id not in excluded_part_ids]
    ratios = _best_part_ratios(student, parts)
    for part in parts:
        ratio = ratios.get(part.id)
        if ratio is None:
            flavour = 'exam_part_untried'
        elif ratio < 0.6:
            flavour = 'exam_part_weak'
        else:
            flavour = 'exam_part_cracked'
        out.append(Candidate('exam_part', part, BASE_SCORES[flavour],
                             estimates.exam_part_minutes(part), flavour))

    section_progress, sections = _section_progress(student, [topic])
    for section in sections:
        done, total = section_progress.get(section.id, (0, 0))
        if total and done >= total:
            continue  # nothing left to do here
        flavour = 'section_fresh' if done == 0 else 'section_partial'
        out.append(Candidate('section', section, BASE_SCORES[flavour],
                             estimates.section_minutes(section, total), flavour))

    card_progress, sets = _flashcard_progress(student, [topic])
    for fset in sets:
        mastered, total = card_progress.get(fset.id, (0, 0))
        if total and mastered / total >= constants.FLASHCARD_DONE_RATIO:
            continue
        out.append(Candidate('flashcard', fset, BASE_SCORES['flashcard'],
                             estimates.flashcard_set_minutes(fset, total),
                             'flashcard'))

    kicks = list(QuickKick.objects.filter(topic=topic))
    seen = set(QuickKickView.objects
               .filter(user=student, quickkick__in=kicks)
               .values_list('quickkick_id', flat=True))
    for kick in kicks:
        if kick.id in seen and not kick.question_id:
            # Already watched and nothing to answer, so rewatching can never
            # register as done -- QuickKickView.viewed_at is set once, on the
            # first view (quickkicks/views.py:56). Scheduling it would hand the
            # student a task they cannot complete.
            continue
        if kick.id in seen:
            flavour = 'quickkick_seen'
        elif kick.question_id:
            flavour = 'quickkick_question'
        else:
            flavour = 'quickkick'
        out.append(Candidate('quickkick', kick, BASE_SCORES[flavour],
                             estimates.quickkick_minutes(kick), flavour))

    return sorted(out, key=lambda c: (-c.score, c.minutes))


# ---------------------------------------------------------------------------
# Building the plan
# ---------------------------------------------------------------------------

def _reserve_checkpoints(student, spec, warnings):
    """Pick this goal's checkpoint and hold back parts for its retries."""
    size = spec.get('checkpoint_size') or constants.DEFAULT_CHECKPOINT_SIZE
    topic = spec['topic']

    pool = checkpoint_service.candidate_parts(topic, plan=None, student=student)
    needed = size * (1 + constants.RETRY_ROUNDS)

    goal = ProposedGoal(
        topic=topic,
        target_mastery=spec.get('target_mastery', constants.DEFAULT_TARGET_MASTERY),
        priority=spec.get('priority', 1),
        checkpoint_size=size,
        pool_available=len(pool),
    )

    if not pool:
        warnings.append(
            f"{topic.name}: no exam parts are tagged to this topic, so it "
            f"cannot have a checkpoint. Tag some parts first, or drop the topic.")
        return goal

    taken = checkpoint_service.spread_across_papers(pool, size)
    goal.checkpoint_parts = taken

    if len(taken) < size:
        warnings.append(
            f"{topic.name}: only {len(taken)} exam part(s) available for a "
            f"checkpoint of {size}.")

    remaining = [p for p in pool if p.id not in {t.id for t in taken}]
    for _ in range(constants.RETRY_ROUNDS):
        round_parts = checkpoint_service.spread_across_papers(remaining, size)
        if len(round_parts) < size:
            break
        goal.reserve_rounds.append(round_parts)
        chosen = {p.id for p in round_parts}
        remaining = [p for p in remaining if p.id not in chosen]

    if len(pool) < needed:
        warnings.append(
            f"{topic.name}: {len(pool)} unseen exam parts available but "
            f"{needed} are needed to cover a checkpoint plus {constants.RETRY_ROUNDS} "
            f"retries. A student who fails twice will run out.")

    return goal


def _allocate(goals, minutes):
    """Split a week's minutes between goals, by priority."""
    weights = [g.priority for g in goals]
    total = sum(weights) or 1
    return [int(minutes * w / total) for w in weights]


def build_plan(student, goal_specs, start_date, deadline,
               weekly_minutes=constants.DEFAULT_WEEKLY_MINUTES):
    """Propose a plan. Reads the student's history; writes nothing."""
    proposal = ProposedPlan()

    if deadline < start_date:
        proposal.warnings.append("The deadline is before the start date.")
        return proposal
    if not goal_specs:
        proposal.warnings.append("No topics were chosen.")
        return proposal

    for spec in goal_specs:
        proposal.goals.append(_reserve_checkpoints(student, spec, proposal.warnings))

    proposal.weeks = build_weeks(start_date, deadline, weekly_minutes)
    if not proposal.weeks:
        proposal.warnings.append("That date range does not contain a full week.")
        return proposal

    excluded = set()
    for goal in proposal.goals:
        excluded |= goal.reserved_part_ids

    pools = [candidates_for_goal(student, g.topic, excluded) for g in proposal.goals]
    total_weeks = len(proposal.weeks)

    for week in proposal.weeks:
        budget = spendable(week)
        shares = _allocate(proposal.goals, budget)
        ramp = (week.index - 1) / max(1, total_weeks - 1) if total_weeks > 1 else 1.0

        for goal_index, (goal, pool) in enumerate(zip(proposal.goals, pools)):
            share = shares[goal_index]
            spent = 0
            placed = 0
            pool.sort(key=lambda c: -c.ramped(ramp))

            while pool and len(week.items) < constants.MAX_ITEMS_PER_WEEK:
                nxt = pool[0]
                over = spent + nxt.minutes
                # Every goal gets at least one item a week while work remains --
                # without this a small share silently drops a topic altogether.
                if placed and over > share * constants.FINAL_ITEM_OVERFLOW:
                    break
                pool.pop(0)
                week.items.append(ProposedItem(
                    kind=nxt.kind, obj=nxt.obj, goal_index=goal_index,
                    estimated_minutes=nxt.minutes))
                spent = over
                placed += 1
                if spent >= share:
                    break

    empty = [w.index for w in proposal.weeks if not w.items]
    if empty:
        proposal.warnings.append(
            f"No work left to fill week(s) {', '.join(str(i) for i in empty)} -- "
            f"the plan may be longer than the material available.")

    return proposal


# ---------------------------------------------------------------------------
# Writing it down
# ---------------------------------------------------------------------------

def persist_plan(plan, proposal):
    """Write a proposal into an existing StudyPlan. Returns the plan.

    Items are validated individually and then bulk-created: ``StudyPlanItem.save``
    calls ``full_clean`` and a loop of saves would run one round trip per item,
    but skipping validation altogether is how a plan ends up with a row whose
    content_type and foreign key disagree.
    """
    from django.db import transaction

    from core import content_links
    from ..models import StudyPlanGoal, StudyPlanItem, StudyPlanWeek
    from . import checkpoints as checkpoint_service

    with transaction.atomic():
        goals = []
        for order, proposed in enumerate(proposal.goals, start=1):
            goals.append(StudyPlanGoal.objects.create(
                plan=plan, topic=proposed.topic,
                target_mastery=proposed.target_mastery,
                checkpoint_size=proposed.checkpoint_size,
                priority=proposed.priority, order=order))

        weeks = []
        for proposed in proposal.weeks:
            weeks.append(StudyPlanWeek.objects.create(
                plan=plan, index=proposed.index,
                start_date=proposed.start_date, end_date=proposed.end_date,
                minutes_budget=proposed.minutes_budget))

        items = []
        for week_model, proposed_week in zip(weeks, proposal.weeks):
            for order, proposed_item in enumerate(proposed_week.items, start=1):
                item = StudyPlanItem(
                    plan=plan, week=week_model,
                    goal=goals[proposed_item.goal_index] if goals else None,
                    content_type=proposed_item.kind,
                    instructions=proposed_item.instructions,
                    estimated_minutes=proposed_item.estimated_minutes,
                    order=order, origin='generated',
                    # Never before the plan itself began: week one starts on a
                    # Monday that can predate the start date, and taking it
                    # would let work done before the plan existed count towards
                    # it -- the very thing the window exists to prevent.
                    available_from=max(week_model.start_date, plan.start_date),
                    due_date=week_model.end_date)
                field = content_links.CONTENT_FK_FIELDS.get(proposed_item.kind)
                if field:
                    setattr(item, field, proposed_item.obj)
                item.full_clean(validate_unique=False)
                items.append(item)
        StudyPlanItem.objects.bulk_create(items)

        for goal, proposed in zip(goals, proposal.goals):
            if proposed.checkpoint_parts:
                checkpoint_service.create_checkpoint(
                    goal, parts=proposed.checkpoint_parts,
                    round_number=1, status='locked')
            for offset, round_parts in enumerate(proposed.reserve_rounds, start=2):
                checkpoint_service.create_checkpoint(
                    goal, parts=round_parts, round_number=offset, status='locked')

    return plan
