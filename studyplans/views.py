"""Pages for study plans: the student's own, and the teacher's view of them.

Function-based views throughout, matching the rest of the project. Access is by
group decorator (students/decorators.py), with a private ownership helper on top
of it -- the decorator says "a teacher", the helper says "this teacher".

Nothing here writes to the database during a GET. Homework's equivalent pages
run their completion check inside the page render (homework/views.py:108), which
means a plain page load mutates data; here a GET computes what to show and the
writes happen in the nightly command or on an explicit POST.
"""
import json
import logging
from datetime import datetime, timedelta

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User

from homework.models import TeacherClass
from interactive_lessons.models import Topic
from students.decorators import student_or_teacher_required, teacher_required

from . import constants
from .models import (
    StudyPlan, StudyPlanCheckpoint, StudyPlanEvent, StudyPlanGoal, StudyPlanItem,
)
from .services import checkpoints as checkpoint_service
from .services import completion, nightly, planner, progress

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Ownership
# ---------------------------------------------------------------------------

def _teacher_profile(request):
    return getattr(request.user, 'teacher_profile', None)

def _teaches(request, student):
    profile = _teacher_profile(request)
    if profile is None:
        return False
    return profile.classes.filter(students=student).exists()


def _owned_plan(request, plan_id):
    """The student's own plan, or one belonging to a student they teach."""
    plan = get_object_or_404(
        StudyPlan.objects.select_related('student', 'teacher', 'subject'),
        id=plan_id)
    if request.user.is_superuser or plan.student_id == request.user.id:
        return plan
    profile = _teacher_profile(request)
    if profile and (plan.teacher_id == profile.id or _teaches(request, plan.student)):
        return plan
    raise PermissionDenied


def _owned_student(request, student_id):
    student = get_object_or_404(User, id=student_id)
    if request.user.is_superuser or student.id == request.user.id:
        return student
    if _teaches(request, student):
        return student
    raise PermissionDenied


def _owned_class(request, class_id):
    teacher_class = get_object_or_404(TeacherClass, id=class_id)
    if request.user.is_superuser:
        return teacher_class
    if teacher_class.teacher != _teacher_profile(request):
        raise PermissionDenied
    return teacher_class


# ============================================================================
# STUDENT VIEWS
# ============================================================================

@student_or_teacher_required
def my_plan(request):
    """The student's current plan: what they have proved, and this week's work."""
    plan = progress.active_plan_for(request.user, getattr(request, 'current_subject', None))
    context = {'card': None, 'week': None, 'plan': None,
               'refresh_after_minutes': constants.REFRESH_THROTTLE_MINUTES}

    if plan:
        context['plan'] = plan
        context['card'] = progress.plan_card(plan)
        context['week'] = progress.week_view(plan, plan.current_week())
        context['needs_refresh'] = (
            plan.last_checked_at is None
            or plan.last_checked_at < timezone.now() - timedelta(
                minutes=constants.REFRESH_THROTTLE_MINUTES))
    else:
        context['other_plans'] = (StudyPlan.objects
                                  .filter(student=request.user)
                                  .exclude(status='draft')
                                  .select_related('subject')[:5])
    return render(request, 'studyplans/my_plan.html', context)


@student_or_teacher_required
def plan_detail(request, plan_id):
    """Every week of one plan."""
    plan = _owned_plan(request, plan_id)
    weeks = [progress.week_view(plan, week)
             for week in plan.weeks.prefetch_related('items')]
    today = timezone.localdate()
    current = plan.current_week(today)
    return render(request, 'studyplans/plan_detail.html', {
        'plan': plan,
        'card': progress.plan_card(plan),
        'weeks': weeks,
        'current_week_id': current.id if current else None,
        'is_owner': plan.student_id == request.user.id,
    })


@student_or_teacher_required
def achievements(request):
    """Every topic this student has ever mastered, across all their plans."""
    return render(request, 'studyplans/achievements.html', {
        'achievements': progress.achievements_for(request.user),
    })


@student_or_teacher_required
def checkpoint_detail(request, checkpoint_id):
    """The parts that make up a checkpoint, and how it went."""
    checkpoint = get_object_or_404(
        StudyPlanCheckpoint.objects.select_related('goal__plan__student',
                                                   'goal__topic'),
        id=checkpoint_id)
    _owned_plan(request, checkpoint.goal.plan_id)
    parts = list(checkpoint.parts.select_related(
        'exam_question_part__question__exam_paper'))
    return render(request, 'studyplans/checkpoint_detail.html', {
        'checkpoint': checkpoint,
        'plan': checkpoint.goal.plan,
        'goal': checkpoint.goal,
        'parts': parts,
        'sat': checkpoint.is_decided,
    })


@require_POST
@student_or_teacher_required
def start_item(request, item_id):
    """Stamp an item as started, then send the student into the work.

    A POST-then-redirect is how we get a dependable "started" signal without
    reaching into four other apps to instrument their pages.
    """
    item = get_object_or_404(StudyPlanItem.objects.select_related('plan'), id=item_id)
    _owned_plan(request, item.plan_id)

    if item.started_at is None:
        item.started_at = timezone.now()
        if item.status == 'pending':
            item.status = 'attempted'
        item.save(update_fields=['started_at', 'status', 'updated_at'])

    return redirect(item.get_content_url())


@require_POST
@student_or_teacher_required
def toggle_item_done(request, item_id):
    """The student's own tick, for written exercises and self-report."""
    item = get_object_or_404(StudyPlanItem.objects.select_related('plan'), id=item_id)
    _owned_plan(request, item.plan_id)

    if item.status == 'done':
        item.status = 'attempted' if item.started_at else 'pending'
        item.completed_at = None
        item.evidence_note = ''
    else:
        item.status = 'done'
        item.completed_at = timezone.now()
        item.evidence_note = 'Ticked by the student'
    item.save(update_fields=['status', 'completed_at', 'evidence_note', 'updated_at'])

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': item.status})
    return redirect(request.META.get('HTTP_REFERER',
                                     reverse('studyplans:my_plan')))


@require_POST
@student_or_teacher_required
def refresh_progress(request, plan_id):
    """Re-check this plan's work now, rather than waiting for the nightly run.

    POST only, deliberately: this writes, and a GET that writes is the bug this
    app exists partly to avoid repeating.
    """
    plan = _owned_plan(request, plan_id)
    items = list(plan.items.exclude(status__in=('done', 'skipped'))
                 .select_related('section', 'exam_question', 'exam_question_part',
                                 'quickkick', 'flashcard_set'))
    changed = completion.persist(items, student=plan.student)

    unlocked = nightly.unlock_due_checkpoints(plan)
    graded = nightly.grade_sat_checkpoints(plan)

    plan.last_checked_at = timezone.now()
    plan.save(update_fields=['last_checked_at'])

    payload = {
        'updated': len(changed),
        'unlocked': len(unlocked),
        'graded': len(graded),
    }
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse(payload)
    if changed or unlocked or graded:
        messages.success(request, "Progress updated.")
    return redirect('studyplans:my_plan')


# ============================================================================
# TEACHER VIEWS
# ============================================================================

@teacher_required
def teacher_dashboard(request):
    """Every plan this teacher is running, with the ones needing attention first."""
    profile = _teacher_profile(request)
    plans = (StudyPlan.objects
             .filter(teacher=profile)
             .exclude(status='archived')
             .select_related('student', 'subject', 'teacher_class')
             .prefetch_related('goals__checkpoints', 'goals__items'))

    rows = []
    for plan in plans:
        card = progress.plan_card(plan)
        attention = plan.goals.filter(needs_teacher_attention=True).count()
        rows.append({'plan': plan, 'card': card, 'attention': attention})
    rows.sort(key=lambda r: (-r['attention'], -r['card']['ready_count'],
                             r['plan'].deadline))

    return render(request, 'studyplans/teacher/dashboard.html', {
        'rows': rows,
        'classes': profile.classes.filter(is_active=True) if profile else [],
    })


@teacher_required
def plan_builder(request):
    """Choose a student or class, the topics, and how long they have."""
    profile = _teacher_profile(request)
    subject = getattr(request, 'current_subject', None)
    topics = Topic.objects.filter(subject=subject) if subject else Topic.objects.all()

    classes = profile.classes.filter(is_active=True).prefetch_related('students')
    students = User.objects.filter(enrolled_classes__teacher=profile).distinct()

    default_start = timezone.localdate()
    return render(request, 'studyplans/teacher/builder.html', {
        'topics': topics.select_related('subject').order_by('order', 'name'),
        'classes': classes,
        'students': students.order_by('username'),
        'default_start': default_start,
        'default_deadline': default_start + timedelta(days=28),
        'default_minutes': constants.DEFAULT_WEEKLY_MINUTES,
        'default_target': constants.DEFAULT_TARGET_MASTERY,
        'default_checkpoint_size': constants.DEFAULT_CHECKPOINT_SIZE,
    })


def _parse_builder_form(request):
    """The builder form, as the planner wants it. Returns (kwargs, errors)."""
    errors = []

    def date_field(name, fallback):
        raw = request.POST.get(name)
        if not raw:
            return fallback
        try:
            return datetime.strptime(raw, '%Y-%m-%d').date()
        except ValueError:
            errors.append(f"{name} is not a date we understand.")
            return fallback

    today = timezone.localdate()
    start_date = date_field('start_date', today)
    deadline = date_field('deadline', today + timedelta(days=28))

    try:
        weekly_minutes = int(request.POST.get('weekly_minutes')
                             or constants.DEFAULT_WEEKLY_MINUTES)
    except ValueError:
        weekly_minutes = constants.DEFAULT_WEEKLY_MINUTES

    topic_ids = request.POST.getlist('topics')
    topics = list(Topic.objects.filter(id__in=topic_ids).select_related('subject'))
    if not topics:
        errors.append("Choose at least one topic.")

    specs = []
    for topic in topics:
        def field(name, default):
            try:
                return int(request.POST.get(f'{name}_{topic.id}') or default)
            except ValueError:
                return default
        specs.append({
            'topic': topic,
            'target_mastery': min(100, max(1, field('target', constants.DEFAULT_TARGET_MASTERY))),
            'priority': min(3, max(1, field('priority', 1))),
            'checkpoint_size': min(10, max(1, field('size', constants.DEFAULT_CHECKPOINT_SIZE))),
        })

    return {
        'specs': specs,
        'start_date': start_date,
        'deadline': deadline,
        'weekly_minutes': weekly_minutes,
        'title': request.POST.get('title', '').strip() or 'Study plan',
        'description': request.POST.get('description', '').strip(),
        'student_id': request.POST.get('student'),
        'class_id': request.POST.get('teacher_class'),
    }, errors


@require_POST
@teacher_required
def plan_preview(request):
    """Show the plan that would be built. Writes nothing."""
    form, errors = _parse_builder_form(request)
    for error in errors:
        messages.error(request, error)
    if errors:
        return redirect('studyplans:plan_builder')

    student_id = form['student_id']
    class_id = form['class_id']
    if not student_id and not class_id:
        messages.error(request, "Choose a student or a class.")
        return redirect('studyplans:plan_builder')

    # Preview against one student: the individual, or the first in the class,
    # so the teacher sees a real plan rather than an average of one.
    if student_id:
        student = _owned_student(request, int(student_id))
    else:
        teacher_class = _owned_class(request, int(class_id))
        student = teacher_class.students.order_by('username').first()
        if student is None:
            messages.error(request, "That class has no students in it yet.")
            return redirect('studyplans:plan_builder')

    proposal = planner.build_plan(
        student, form['specs'], form['start_date'], form['deadline'],
        form['weekly_minutes'])

    return render(request, 'studyplans/teacher/preview.html', {
        'proposal': proposal,
        'student': student,
        'form': form,
        'is_class': bool(class_id and not student_id),
        'class_id': class_id,
        'payload': json.dumps({
            'title': form['title'],
            'description': form['description'],
            'start_date': form['start_date'].isoformat(),
            'deadline': form['deadline'].isoformat(),
            'weekly_minutes': form['weekly_minutes'],
            'student': student_id,
            'teacher_class': class_id,
            'specs': [{'topic': s['topic'].id,
                       'target_mastery': s['target_mastery'],
                       'priority': s['priority'],
                       'checkpoint_size': s['checkpoint_size']}
                      for s in form['specs']],
        }),
    })


def _create_one_plan(request, student, form, source_template=None,
                     teacher_class=None):
    """Build and save a plan for one student, against their own history."""
    proposal = planner.build_plan(
        student, form['specs'], form['start_date'], form['deadline'],
        form['weekly_minutes'])
    subject = form['specs'][0]['topic'].subject or getattr(
        request, 'current_subject', None)

    plan = StudyPlan.objects.create(
        student=student, teacher=_teacher_profile(request), subject=subject,
        title=form['title'], description=form['description'],
        start_date=form['start_date'], deadline=form['deadline'],
        weekly_minutes=form['weekly_minutes'], status='active',
        teacher_class=teacher_class, source_template=source_template)
    planner.persist_plan(plan, proposal)
    StudyPlanEvent.log(plan, 'created',
                       f"Plan created with {plan.goals.count()} topic(s)")
    return plan


@require_POST
@teacher_required
def plan_create(request):
    """Save the previewed plan."""
    form, errors = _parse_builder_form(request)
    for error in errors:
        messages.error(request, error)
    if errors:
        return redirect('studyplans:plan_builder')

    student_id = request.POST.get('student')
    class_id = request.POST.get('teacher_class')

    if student_id:
        student = _owned_student(request, int(student_id))
        plan = _create_one_plan(request, student, form)
        messages.success(request, f"Plan set for {student.username}.")
        return redirect('studyplans:plan_manage', plan_id=plan.id)

    if class_id:
        teacher_class = _owned_class(request, int(class_id))
        return _rollout(request, teacher_class, form)

    messages.error(request, "Choose a student or a class.")
    return redirect('studyplans:plan_builder')


def _rollout(request, teacher_class, form, source_template=None):
    """One plan per student, each generated against that student's own history.

    Not a copy: the point of the feature is that two students on the same class
    plan get different work, because they arrive at it from different places.
    """
    made, skipped = 0, 0
    with transaction.atomic():
        template = source_template
        for student in teacher_class.students.order_by('username'):
            # Two guards, because they catch different mistakes. The template
            # check stops a re-run of *this* rollout; the title check stops a
            # double-clicked form, where each POST would otherwise mint a fresh
            # template and so never collide with the first.
            if template and StudyPlan.objects.filter(
                    student=student, source_template=template).exists():
                skipped += 1
                continue
            if StudyPlan.objects.filter(
                    student=student, teacher_class=teacher_class,
                    title=form['title'], status='active').exists():
                skipped += 1
                continue
            plan = _create_one_plan(request, student, form,
                                    source_template=template,
                                    teacher_class=teacher_class)
            if template is None:
                template = plan
                plan.source_template = plan
                plan.save(update_fields=['source_template'])
            StudyPlanEvent.log(plan, 'rollout',
                               f"Rolled out to {teacher_class.name}")
            made += 1

    messages.success(
        request,
        f"Set {made} plan(s) for {teacher_class.name}."
        + (f" {skipped} student(s) already had one." if skipped else ""))
    return redirect('studyplans:teacher_dashboard')


@teacher_required
def plan_manage(request, plan_id):
    """The teacher's view of one plan, and the controls for changing it."""
    plan = _owned_plan(request, plan_id)
    weeks = [progress.week_view(plan, week)
             for week in plan.weeks.prefetch_related('items')]
    goals = [progress.goal_state(goal)
             for goal in plan.goals.select_related('topic')
             .prefetch_related('items', 'checkpoints')]
    return render(request, 'studyplans/teacher/plan_manage.html', {
        'plan': plan,
        'card': progress.plan_card(plan),
        'goals': goals,
        'weeks': weeks,
        'events': plan.events.all()[:30],
    })


@require_POST
@teacher_required
def manage_checkpoint(request, plan_id, checkpoint_id):
    """Unlock a checkpoint early, or void a result."""
    plan = _owned_plan(request, plan_id)
    checkpoint = get_object_or_404(
        StudyPlanCheckpoint, id=checkpoint_id, goal__plan=plan)
    action = request.POST.get('action')

    if action == 'unlock':
        checkpoint_service.unlock(checkpoint)
        messages.success(request, "Checkpoint unlocked.")
    elif action == 'void':
        checkpoint.status = 'voided'
        checkpoint.save(update_fields=['status'])
        goal = checkpoint.goal
        if goal.mastered_at and goal.mastery_score == checkpoint.score:
            goal.mastered_at = None
            goal.mastery_score = None
            goal.save(update_fields=['mastered_at', 'mastery_score'])
        StudyPlanEvent.log(plan, 'teacher_edit',
                           f"{checkpoint.goal.topic.name}: checkpoint "
                           f"{checkpoint.round} voided", checkpoint=checkpoint)
        messages.success(request, "Checkpoint voided.")
    else:
        messages.error(request, "Unknown action.")

    return redirect('studyplans:plan_manage', plan_id=plan.id)


@require_POST
@teacher_required
def remove_item(request, plan_id, item_id):
    """Drop an item from the plan without destroying the record of it."""
    plan = _owned_plan(request, plan_id)
    item = get_object_or_404(StudyPlanItem, id=item_id, plan=plan)
    item.status = 'skipped'
    item.save(update_fields=['status', 'updated_at'])
    StudyPlanEvent.log(plan, 'teacher_edit',
                       f"Removed: {item.get_content_display()}", item=item)
    messages.success(request, "Item removed from the plan.")
    return redirect('studyplans:plan_manage', plan_id=plan.id)


@require_POST
@teacher_required
def run_now(request, plan_id):
    """Run tonight's checks against this plan now."""
    plan = _owned_plan(request, plan_id)
    summary = nightly.run_for_plan(plan)
    messages.success(
        request,
        f"Checked: {summary['completed']} item(s) done, "
        f"{summary['unlocked']} checkpoint(s) unlocked, "
        f"{summary['graded']} marked, {summary['carried']} carried forward.")
    return redirect('studyplans:plan_manage', plan_id=plan.id)


@teacher_required
def class_oversight(request, class_id):
    """Students down the side, topics across the top, state in the cells."""
    teacher_class = _owned_class(request, class_id)
    students = list(teacher_class.students.order_by('username'))
    plans = (StudyPlan.objects
             .filter(student__in=students, teacher_class=teacher_class)
             .exclude(status='archived')
             .select_related('student')
             .prefetch_related('goals__topic', 'goals__items', 'goals__checkpoints'))

    by_student = {plan.student_id: plan for plan in plans}
    topics, rows = [], []
    for plan in plans:
        for goal in plan.goals.all():
            if goal.topic not in topics:
                topics.append(goal.topic)

    for student in students:
        plan = by_student.get(student.id)
        cells = []
        if plan:
            states = {s['topic'].id: s for s in progress.plan_card(plan)['goals']}
            cells = [states.get(topic.id) for topic in topics]
        rows.append({'student': student, 'plan': plan, 'cells': cells})

    return render(request, 'studyplans/teacher/class_oversight.html', {
        'teacher_class': teacher_class,
        'topics': topics,
        'rows': rows,
    })


@teacher_required
def student_oversight(request, student_id):
    """One student: their plans, what they have proved, and what the plan did."""
    student = _owned_student(request, student_id)
    plans = (StudyPlan.objects.filter(student=student)
             .select_related('subject')
             .prefetch_related('goals__topic', 'goals__items', 'goals__checkpoints'))
    return render(request, 'studyplans/teacher/student_oversight.html', {
        'student': student,
        'cards': [progress.plan_card(plan) for plan in plans],
        'achievements': progress.achievements_for(student),
    })


@require_GET
@teacher_required
def topic_candidates(request, topic_id):
    """What a topic has to offer this student, for the builder's warnings."""
    topic = get_object_or_404(Topic, id=topic_id)
    student_id = request.GET.get('student')
    student = _owned_student(request, int(student_id)) if student_id else None

    parts = checkpoint_service.candidate_parts(topic, plan=None, student=student)
    size = int(request.GET.get('size') or constants.DEFAULT_CHECKPOINT_SIZE)
    needed = size * (1 + constants.RETRY_ROUNDS)

    return JsonResponse({
        'topic': topic.name,
        'unseen_exam_parts': len(parts),
        'needed_for_retries': needed,
        'sufficient': len(parts) >= needed,
        'can_start': len(parts) >= size,
        'suggested': [
            {'id': p.id,
             'label': (f"{p.question.exam_paper.year} "
                       f"{p.question.exam_paper.get_paper_type_display()} "
                       f"Q{p.question.question_number}{p.label}"),
             'marks': p.max_marks}
            for p in checkpoint_service.spread_across_papers(parts, size)
        ],
    })
