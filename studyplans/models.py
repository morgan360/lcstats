"""A teacher-set, multi-week plan that proves a student has mastered a topic.

The loop is deliberately simple: a teacher names the topics a student should get
solid on, the plan hands out work week by week, and each topic ends in a
**checkpoint** -- two or three real exam parts the student sits. Passing the
checkpoint *is* mastery. Nothing here infers mastery from a blend of attempt
history, because a number a teacher cannot check by hand is a number they will
not trust.

Two things follow from that and are load-bearing:

* A checkpoint's ``pass_mark``, its parts' ``marks_possible`` and its per-part
  results are all **snapshots taken at the time**. The achievements page is a
  permanent record, and editing a target or a marking scheme next term must not
  reach back and change what a student earned last term.
* Parts reserved for a checkpoint are never handed out as practice. A capstone
  sat on questions the student already worked through, solution open, proves
  nothing.

Plans key off ``User`` rather than ``StudentProfile``: profiles are created
lazily on first dashboard load (students/views.py), so a student who has never
opened theirs has none, and a foreign key to it would be un-creatable for them.
"""
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from core import content_links
from exam_papers.models import ExamQuestion, ExamQuestionPart
from flashcards.models import FlashcardSet
from interactive_lessons.models import Section, Topic
from quickkicks.models import QuickKick

from . import constants


class StudyPlan(models.Model):
    """One student's plan, over a run of weeks, towards a set of topics."""

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('archived', 'Archived'),
    ]

    student = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='study_plans')
    teacher = models.ForeignKey(
        'homework.TeacherProfile', on_delete=models.PROTECT,
        related_name='study_plans',
        help_text="Teacher who set this plan")
    subject = models.ForeignKey(
        'core.Subject', on_delete=models.PROTECT, related_name='study_plans')
    teacher_class = models.ForeignKey(
        'homework.TeacherClass', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='study_plans',
        help_text="Class this plan was rolled out to, if any")
    source_template = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='rollouts',
        help_text="The plan this one was generated from during a class rollout")

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    start_date = models.DateField()
    deadline = models.DateField()
    weekly_minutes = models.PositiveSmallIntegerField(
        default=constants.DEFAULT_WEEKLY_MINUTES,
        validators=[MinValueValidator(30), MaxValueValidator(1200)],
        help_text="Minutes of work per week this student has committed to")

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    is_locked = models.BooleanField(
        default=False,
        help_text="The nightly run leaves a locked plan exactly as it is")

    last_checked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Study Plan"
        ordering = ['-start_date', '-id']
        indexes = [
            models.Index(fields=['student', 'status']),
            models.Index(fields=['status', 'deadline']),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(deadline__gte=models.F('start_date')),
                name='studyplan_deadline_after_start',
            ),
            # Idempotency for class rollout at the database level: posting the
            # rollout form twice cannot produce two plans for one student.
            # Deliberately unconditional -- MySQL silently refuses to build a
            # unique constraint that carries a condition (models.W036), and it
            # is not needed: both MySQL and PostgreSQL treat NULLs as distinct,
            # so a student's own hand-made plans (source_template NULL) never
            # collide with each other, while two rollouts of one template do.
            models.UniqueConstraint(
                fields=['student', 'source_template'],
                name='studyplan_one_rollout_per_student',
            ),
        ]

    def __str__(self):
        return f"{self.title} - {self.student.username}"

    @property
    def is_running(self):
        return self.status == 'active' and not self.is_locked

    @property
    def days_remaining(self):
        return (self.deadline - timezone.localdate()).days

    def current_week(self, today=None):
        """The week containing today, or the nearest one at either end."""
        today = today or timezone.localdate()
        weeks = list(self.weeks.all())
        if not weeks:
            return None
        for week in weeks:
            if week.start_date <= today <= week.end_date:
                return week
        if today < weeks[0].start_date:
            return weeks[0]
        return weeks[-1]

    def goal_progress(self):
        """(mastered, total) goals -- what the progress card leads with."""
        goals = list(self.goals.all())
        return sum(1 for g in goals if g.mastered_at), len(goals)


class StudyPlanGoal(models.Model):
    """One topic this plan is meant to get the student solid on."""

    PRIORITY_CHOICES = [(1, 'Normal'), (2, 'High'), (3, 'Critical')]

    plan = models.ForeignKey(StudyPlan, on_delete=models.CASCADE, related_name='goals')
    topic = models.ForeignKey(
        Topic, on_delete=models.PROTECT, related_name='study_plan_goals')

    target_mastery = models.PositiveSmallIntegerField(
        default=constants.DEFAULT_TARGET_MASTERY,
        validators=[MinValueValidator(1), MaxValueValidator(100)],
        help_text="Percentage on the checkpoint that counts as mastered")
    checkpoint_size = models.PositiveSmallIntegerField(
        default=constants.DEFAULT_CHECKPOINT_SIZE,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text="How many exam parts make up each checkpoint")
    priority = models.PositiveSmallIntegerField(default=1, choices=PRIORITY_CHOICES)
    order = models.PositiveSmallIntegerField(default=0)

    # Written when a checkpoint is passed. Denormalised so the progress card and
    # the achievements page stay single cheap queries.
    mastered_at = models.DateTimeField(null=True, blank=True)
    mastery_score = models.FloatField(null=True, blank=True)

    needs_teacher_attention = models.BooleanField(default=False)
    attention_reason = models.CharField(max_length=200, blank=True)

    class Meta:
        verbose_name = "Study Plan Goal"
        ordering = ['plan', 'order', 'id']
        constraints = [
            models.UniqueConstraint(
                fields=['plan', 'topic'], name='studyplangoal_one_per_topic'),
        ]

    def __str__(self):
        return f"{self.plan.title}: {self.topic.name}"

    @property
    def is_mastered(self):
        return self.mastered_at is not None

    def latest_checkpoint(self):
        return self.checkpoints.order_by('-round').first()

    def flag(self, reason):
        """Hand this goal to the teacher rather than guessing."""
        self.needs_teacher_attention = True
        self.attention_reason = reason[:200]
        self.save(update_fields=['needs_teacher_attention', 'attention_reason'])


class StudyPlanCheckpoint(models.Model):
    """The exam parts that decide whether a topic counts as mastered.

    ``pass_mark`` is copied from the goal when the checkpoint is created, not
    read through the relation, so that raising a goal's target next month cannot
    retroactively turn last month's pass into a fail.
    """

    STATUS_CHOICES = [
        ('locked', 'Locked'),
        ('ready', 'Ready to sit'),
        ('passed', 'Passed'),
        ('failed', 'Not passed'),
        ('voided', 'Voided by teacher'),
    ]

    goal = models.ForeignKey(
        StudyPlanGoal, on_delete=models.CASCADE, related_name='checkpoints')
    round = models.PositiveSmallIntegerField(
        default=1, help_text="1 for the first attempt, 2 after a fail, and so on")

    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default='locked')
    pass_mark = models.PositiveSmallIntegerField(
        help_text="Percentage needed to pass, frozen when this checkpoint was set")

    unlocked_at = models.DateTimeField(
        null=True, blank=True,
        help_text="Only work done after this counts towards the result")
    sat_at = models.DateTimeField(null=True, blank=True)

    marks_awarded = models.FloatField(null=True, blank=True)
    marks_possible = models.FloatField(null=True, blank=True)
    score = models.FloatField(null=True, blank=True, help_text="Percentage, 0-100")
    is_clean = models.BooleanField(
        default=True,
        help_text="False if a marking scheme was opened while sitting this")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Study Plan Checkpoint"
        ordering = ['goal', 'round']
        indexes = [models.Index(fields=['goal', 'status'])]
        constraints = [
            models.UniqueConstraint(
                fields=['goal', 'round'], name='studyplancheckpoint_one_per_round'),
        ]

    def __str__(self):
        return f"{self.goal.topic.name} checkpoint {self.round} ({self.get_status_display()})"

    @property
    def is_decided(self):
        """A settled result. The nightly run must not grade these again."""
        return self.status in ('passed', 'failed', 'voided')

    @property
    def total_marks(self):
        return sum(p.marks_possible for p in self.parts.all())


class StudyPlanCheckpointPart(models.Model):
    """One exam part within a checkpoint, and how the student did on it.

    ``marks_possible`` is a snapshot: a teacher filling in a part's ``max_marks``
    next term must not change what a checkpoint was worth when it was sat.
    """

    checkpoint = models.ForeignKey(
        StudyPlanCheckpoint, on_delete=models.CASCADE, related_name='parts')
    exam_question_part = models.ForeignKey(
        ExamQuestionPart, on_delete=models.CASCADE, related_name='checkpoint_parts')
    order = models.PositiveSmallIntegerField(default=0)
    marks_possible = models.PositiveSmallIntegerField()

    # Frozen when the checkpoint is graded.
    marks_awarded = models.FloatField(null=True, blank=True)
    score = models.FloatField(null=True, blank=True)
    attempted_at = models.DateTimeField(null=True, blank=True)
    hint_used = models.BooleanField(default=False)
    solution_viewed = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Study Plan Checkpoint Part"
        ordering = ['checkpoint', 'order', 'id']
        constraints = [
            models.UniqueConstraint(
                fields=['checkpoint', 'exam_question_part'],
                name='studyplancheckpointpart_once_per_checkpoint'),
        ]

    def __str__(self):
        return f"{self.checkpoint} - {self.exam_question_part}"

    @property
    def is_attempted(self):
        return self.attempted_at is not None


class StudyPlanWeek(models.Model):
    """A Monday-to-Sunday slice of the plan, with its own time budget."""

    plan = models.ForeignKey(StudyPlan, on_delete=models.CASCADE, related_name='weeks')
    index = models.PositiveSmallIntegerField(help_text="1 for the first week")
    start_date = models.DateField()
    end_date = models.DateField()
    minutes_budget = models.PositiveSmallIntegerField()
    focus_note = models.TextField(blank=True)

    class Meta:
        verbose_name = "Study Plan Week"
        ordering = ['plan', 'index']
        constraints = [
            models.UniqueConstraint(
                fields=['plan', 'index'], name='studyplanweek_index_per_plan'),
        ]

    def __str__(self):
        return f"{self.plan.title} week {self.index}"

    def contains(self, day):
        return self.start_date <= day <= self.end_date


class StudyPlanItem(models.Model):
    """One piece of work: a section, an exam part, a flashcard set, and so on.

    ``available_from`` is what stops a plan completing itself the moment it is
    created: only work done on or after that date counts towards this item.
    Homework's equivalent check has no such window and so is satisfied by
    attempts made months earlier.
    """

    ORIGIN_CHOICES = [
        ('generated', 'Generated'),
        ('teacher', 'Chosen by teacher'),
        ('revisit', 'Revisit after a checkpoint'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Not started'),
        ('attempted', 'Started'),
        ('done', 'Done'),
        ('skipped', 'No longer needed'),
    ]

    # Denormalised alongside `week`: nearly every query is per-plan, and `week`
    # moves when work is carried forward while `plan` never does.
    plan = models.ForeignKey(StudyPlan, on_delete=models.CASCADE, related_name='items')
    week = models.ForeignKey(
        StudyPlanWeek, on_delete=models.CASCADE, related_name='items',
        null=True, blank=True, help_text="Empty means backlog")
    goal = models.ForeignKey(
        StudyPlanGoal, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='items')

    content_type = models.CharField(
        max_length=20, choices=content_links.CONTENT_KIND_CHOICES)
    section = models.ForeignKey(
        Section, on_delete=models.CASCADE, null=True, blank=True,
        related_name='study_plan_items')
    exam_question = models.ForeignKey(
        ExamQuestion, on_delete=models.CASCADE, null=True, blank=True,
        related_name='study_plan_items')
    exam_question_part = models.ForeignKey(
        ExamQuestionPart, on_delete=models.CASCADE, null=True, blank=True,
        related_name='study_plan_items')
    quickkick = models.ForeignKey(
        QuickKick, on_delete=models.CASCADE, null=True, blank=True,
        related_name='study_plan_items', verbose_name="QuickFlicks")
    flashcard_set = models.ForeignKey(
        FlashcardSet, on_delete=models.CASCADE, null=True, blank=True,
        related_name='study_plan_items')
    instructions = models.TextField(blank=True)

    # Stored, not computed: filling in a part's max_marks later must not
    # rewrite the budget of a week that has already been worked.
    estimated_minutes = models.PositiveSmallIntegerField(default=10)
    order = models.PositiveSmallIntegerField(default=0)
    origin = models.CharField(max_length=12, choices=ORIGIN_CHOICES, default='generated')
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default='pending')

    available_from = models.DateField()
    due_date = models.DateField()
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    evidence_score = models.FloatField(null=True, blank=True)
    evidence_note = models.CharField(
        max_length=200, blank=True,
        help_text="Why this counted as done, in words the student can read")

    carried_over_count = models.PositiveSmallIntegerField(default=0)
    needs_teacher_attention = models.BooleanField(default=False)
    student_note = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Study Plan Item"
        ordering = ['plan', 'week', 'order', 'id']
        indexes = [
            models.Index(fields=['plan', 'status']),
            models.Index(fields=['week', 'order']),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(due_date__gte=models.F('available_from')),
                name='studyplanitem_due_after_available',
            ),
        ]

    def __str__(self):
        return f"{self.plan.title}: {self.get_content_display()}"

    # -- content dispatch, shared with homework via core.content_links --------

    def get_content_display(self):
        return content_links.content_display(
            self.content_type, content_links.refs_from(self), self.instructions)

    def get_content_url(self):
        return content_links.content_url(
            self.content_type, content_links.refs_from(self))

    @property
    def content_object(self):
        return content_links.content_object(
            self.content_type, content_links.refs_from(self))

    def clean(self):
        errors = content_links.validate_refs(
            self.content_type, content_links.refs_from(self), self.instructions)
        if errors:
            raise ValidationError(errors)
        content_links.null_unmatched(self.content_type, self)

        if self.week_id and self.plan_id and self.week.plan_id != self.plan_id:
            raise ValidationError(
                {'week': 'That week belongs to a different plan'})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    # -- state ---------------------------------------------------------------

    @property
    def is_done(self):
        return self.status == 'done'

    @property
    def is_locked_for_automation(self):
        """Work the nightly run must leave alone.

        A teacher's own choice, and anything the student has already touched.
        """
        return (self.origin == 'teacher'
                or self.status in ('done', 'skipped')
                or self.started_at is not None
                or bool(self.student_note.strip()))

    def mark_done(self, score=None, note='', when=None):
        self.status = 'done'
        self.completed_at = when or timezone.now()
        self.evidence_score = score
        self.evidence_note = note[:200]
        self.save(update_fields=['status', 'completed_at', 'evidence_score',
                                 'evidence_note', 'updated_at'])


class StudyPlanEvent(models.Model):
    """What the plan did, and why -- shown to the teacher on the oversight page.

    A plan that rearranges itself overnight with no account of what it changed
    is one a teacher stops trusting the first time it surprises them.
    """

    KIND_CHOICES = [
        ('created', 'Plan created'),
        ('rollout', 'Rolled out to a class'),
        ('carried', 'Work carried forward'),
        ('injected', 'Extra work added'),
        ('checkpoint_unlocked', 'Checkpoint unlocked'),
        ('checkpoint_passed', 'Checkpoint passed'),
        ('checkpoint_failed', 'Checkpoint not passed'),
        ('goal_mastered', 'Topic mastered'),
        ('teacher_edit', 'Teacher edited the plan'),
        ('attention', 'Needs the teacher'),
    ]

    plan = models.ForeignKey(StudyPlan, on_delete=models.CASCADE, related_name='events')
    kind = models.CharField(max_length=24, choices=KIND_CHOICES)
    message = models.CharField(max_length=300)
    item = models.ForeignKey(
        StudyPlanItem, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='events')
    checkpoint = models.ForeignKey(
        StudyPlanCheckpoint, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='events')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Study Plan Event"
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['plan', '-created_at'])]

    def __str__(self):
        return f"{self.plan.title}: {self.message}"

    @classmethod
    def log(cls, plan, kind, message, item=None, checkpoint=None):
        return cls.objects.create(
            plan=plan, kind=kind, message=message[:300],
            item=item, checkpoint=checkpoint)
