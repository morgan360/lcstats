"""Turning "get solid on these topics by December" into ten MicroBadges a topic.

``build_plan`` is pure: it reads the student's history and returns a proposal,
and creates nothing. That is what lets the teacher's preview page and the
persisting step share one code path, and it is what makes the whole thing
testable without a database full of half-made plans.

Which work is chosen is ranked on what the student has already done; the order
it is bundled in is a teaching judgement, not an optimisation. Recall material
comes early, exam parts come late, and anything the student has already
cracked comes last if at all. Parts held back for the Badge Test never appear
here: a test sat on a question they have already worked through with the
marking scheme open proves nothing.
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
class ProposedGoal:
    topic: object
    target_mastery: int
    priority: int
    checkpoint_size: int
    checkpoint_parts: list = field(default_factory=list)
    reserve_rounds: list = field(default_factory=list)
    pool_available: int = 0
    #: Ten lists of ProposedItem, one per MicroBadge; a list may be empty.
    badges: list = field(default_factory=list)

    @property
    def minutes(self):
        return sum(i.estimated_minutes for badge in self.badges for i in badge)

    @property
    def reserved_part_ids(self):
        ids = {p.id for p in self.checkpoint_parts}
        for round_parts in self.reserve_rounds:
            ids |= {p.id for p in round_parts}
        return ids


@dataclass
class ProposedPlan:
    goals: list = field(default_factory=list)
    warnings: list = field(default_factory=list)

    @property
    def total_items(self):
        return sum(len(badge) for g in self.goals for badge in g.badges)


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

    @property
    def stage(self):
        """Where it sits in teaching order: meet it, recall it, practise it,
        then prove it on exam questions."""
        return STAGES.get(self.kind, len(STAGES))


#: Teaching order within a topic's ten MicroBadges.
STAGES = {'quickkick': 0, 'flashcard': 1, 'section': 2,
          'exam_part': 3, 'exam_question': 3}


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
    """Split minutes between goals, by priority."""
    weights = [g.priority for g in goals]
    total = sum(weights) or 1
    return [int(minutes * w / total) for w in weights]


def plan_minutes(start_date, deadline, weekly_minutes):
    """The student's whole commitment over the run, at their weekly rate."""
    days = (deadline - start_date).days + 1
    return int(weekly_minutes * days / 7)


def choose(pool, budget, at_least=constants.MICROBADGES_PER_TOPIC):
    """The best of a topic's candidates, up to its share of the time.

    Always at least enough to give each MicroBadge something, where the topic
    has that much -- a short plan should mean small MicroBadges, not missing
    ones.
    """
    chosen, spent = [], 0
    for candidate in pool:
        if len(chosen) >= at_least and spent + candidate.minutes > budget:
            continue
        chosen.append(candidate)
        spent += candidate.minutes
    return chosen


def bundle(items, count=constants.MICROBADGES_PER_TOPIC, minutes=lambda i: i.minutes):
    """Cut an ordered list into ``count`` runs of roughly equal time.

    Contiguous, so the teaching order survives; none empty while there are
    items enough; with fewer items than MicroBadges, one each and the rest
    empty.
    """
    groups = [[] for _ in range(count)]
    remaining = list(items)
    for index in range(count):
        groups_left = count - index
        if not remaining:
            break
        if len(remaining) <= groups_left:
            groups[index].append(remaining.pop(0))
            continue
        share = sum(minutes(i) for i in remaining) / groups_left
        group, spent = groups[index], 0
        while remaining and len(remaining) > groups_left - 1:
            nxt = remaining[0]
            if group and spent + minutes(nxt) / 2 > share:
                break
            group.append(remaining.pop(0))
            spent += minutes(nxt)
    return groups


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

    excluded = set()
    for goal in proposal.goals:
        excluded |= goal.reserved_part_ids

    budgets = _allocate(proposal.goals,
                        plan_minutes(start_date, deadline, weekly_minutes))
    slots = constants.MICROBADGES_PER_TOPIC

    for goal_index, (goal, budget) in enumerate(zip(proposal.goals, budgets)):
        pool = candidates_for_goal(student, goal.topic, excluded)
        chosen = choose(pool, budget)
        chosen.sort(key=lambda c: (c.stage, -c.score, c.minutes))
        goal.badges = [
            [ProposedItem(kind=c.kind, obj=c.obj, goal_index=goal_index,
                          estimated_minutes=c.minutes) for c in group]
            for group in bundle(chosen, slots)
        ]
        if len(chosen) < slots:
            proposal.warnings.append(
                f"{goal.topic.name}: only {len(chosen)} piece(s) of practice left "
                f"for this student, so MicroBadges {len(chosen) + 1}-{slots} are "
                f"empty. Add work to them from the plan page, or award them.")

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
    from ..models import StudyPlanGoal, StudyPlanItem, StudyPlanMicroBadge
    from . import checkpoints as checkpoint_service
    from . import microbadges

    with transaction.atomic():
        goals = []
        for order, proposed in enumerate(proposal.goals, start=1):
            goals.append(StudyPlanGoal.objects.create(
                plan=plan, topic=proposed.topic,
                target_mastery=proposed.target_mastery,
                checkpoint_size=proposed.checkpoint_size,
                priority=proposed.priority, order=order))

        items = []
        targets = microbadges.target_dates(plan.start_date, plan.deadline)
        for goal, proposed in zip(goals, proposal.goals):
            for number, (target, contents) in enumerate(
                    zip(targets, proposed.badges), start=1):
                badge = StudyPlanMicroBadge.objects.create(
                    goal=goal, number=number, kind='core', target_date=target)
                for order, proposed_item in enumerate(contents, start=1):
                    item = StudyPlanItem(
                        plan=plan, goal=goal, micro_badge=badge,
                        content_type=proposed_item.kind,
                        instructions=proposed_item.instructions,
                        estimated_minutes=proposed_item.estimated_minutes,
                        order=order, origin='generated',
                        # Only work done once the plan began counts; a
                        # MicroBadge's target date is a pace, not a window.
                        available_from=plan.start_date,
                        due_date=target)
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
