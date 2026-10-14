# exam_papers/models.py
import re
import uuid
from datetime import timedelta

from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.utils import timezone
from interactive_lessons.models import Topic
from students.storage import private_storage


class ExamPaper(models.Model):
    """
    Represents a complete Leaving Certificate exam paper.
    Links multiple questions together into a cohesive exam experience.
    """
    PAPER_TYPE_CHOICES = [
        ('p1', 'Paper 1'),
        ('p2', 'Paper 2'),
    ]

    subject = models.ForeignKey(
        'core.Subject',
        on_delete=models.CASCADE,
        related_name='exam_papers',
        null=True,  # Temporary: will assign all existing to Maths, then remove
        blank=True,
        help_text="Subject this exam paper belongs to (Maths, Physics, etc.)"
    )
    year = models.IntegerField(help_text="Year of the exam (e.g., 2024)")
    paper_type = models.CharField(
        max_length=10,
        choices=PAPER_TYPE_CHOICES,
        help_text="Paper 1 or Paper 2"
    )
    is_deferred = models.BooleanField(
        default=False,
        help_text="Is this a deferred exam paper?"
    )
    title = models.CharField(
        max_length=255,
        help_text="Display title (e.g., 'Leaving Certificate 2024 Paper 1')"
    )
    slug = models.SlugField(unique=True, blank=True)

    # Timing
    time_limit_minutes = models.IntegerField(
        default=150,
        help_text="Total time allowed for this paper in minutes"
    )

    # Marks
    total_marks = models.IntegerField(
        help_text="Total marks available on this paper"
    )

    # Instructions and metadata
    instructions = models.TextField(
        blank=True,
        help_text="General instructions for the paper (e.g., 'Answer 6 out of 8 questions')"
    )

    # PDF reference
    source_pdf = models.FileField(
        upload_to='exam_papers/pdfs/',
        blank=True,
        null=True,
        help_text="Original exam paper PDF"
    )

    # Marking scheme PDF (uploaded separately)
    marking_scheme_pdf = models.FileField(
        upload_to='exam_papers/marking_schemes/pdfs/',
        blank=True,
        null=True,
        help_text="Official marking scheme PDF for this paper"
    )

    # Display options
    is_published = models.BooleanField(
        default=False,
        help_text="Whether this paper is visible to students"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-year', 'paper_type', 'is_deferred']
        unique_together = ('year', 'paper_type', 'is_deferred')

    def __str__(self):
        deferred_suffix = " (Deferred)" if self.is_deferred else ""
        return f"{self.year} {self.get_paper_type_display()}{deferred_suffix}"

    def save(self, *args, **kwargs):
        if not self.slug:
            deferred_suffix = "-deferred" if self.is_deferred else ""
            self.slug = slugify(f"{self.year}-{self.paper_type}{deferred_suffix}")
        if not self.title:
            deferred_text = " Deferred" if self.is_deferred else ""
            self.title = f"Leaving Certificate {self.year}{deferred_text} {self.get_paper_type_display()}"
        super().save(*args, **kwargs)


def topic_errors(paper, *topics):
    """Why these main/secondary/need-to-know topics cannot go together, if
    they cannot: {field: message}. Shared by the model and the save endpoint.
    """
    fields = ('topic', 'secondary_topic', 'need_to_know_topic')
    names = ('main topic', 'secondary topic', 'need-to-know topic')
    errors, seen = {}, {}
    for field, name, topic in zip(fields, names, topics):
        if topic is None:
            continue
        if paper is not None and paper.subject_id and topic.subject_id != paper.subject_id:
            errors[field] = f"{topic.name} is not a {paper.subject} topic"
        elif topic.pk in seen:
            errors[field] = f"{topic.name} is already the {seen[topic.pk]}"
        seen.setdefault(topic.pk, name)
    return errors


class ExamQuestion(models.Model):
    """
    Represents a question on an exam paper.
    Can have multiple parts (a), (b), (c), etc.
    """
    exam_paper = models.ForeignKey(
        ExamPaper,
        on_delete=models.CASCADE,
        related_name='questions'
    )

    # Question identification
    question_number = models.PositiveIntegerField(
        help_text="Question number on the paper (e.g., 1, 2, 3)"
    )

    # Topic classification. A question has one main topic, optionally a
    # secondary one it is also listed under when list_under_secondary is
    # ticked, and optionally a need-to-know topic that plays a minor part:
    # shown on the question, never used to list it.
    topic = models.ForeignKey(
        Topic,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='exam_questions',
        verbose_name="Main topic",
        help_text="The topic this question is mainly about"
    )
    secondary_topic = models.ForeignKey(
        Topic,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='secondary_exam_questions',
        help_text="A second significant topic in this question"
    )
    list_under_secondary = models.BooleanField(
        default=False,
        help_text="Also list this question under its secondary topic"
    )
    need_to_know_topic = models.ForeignKey(
        Topic,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='need_to_know_exam_questions',
        help_text="A topic that plays a minor part; shown, never listed under"
    )

    # Question content
    title = models.CharField(
        max_length=255,
        blank=True,
        help_text="Optional title/description of the question"
    )
    image = models.ImageField(
        upload_to='exam_papers/questions/',
        blank=True,
        null=True,
        help_text="Diagram or image for the question stem"
    )

    # Marks
    total_marks = models.IntegerField(
        help_text="Total marks for this question (sum of all parts)"
    )

    # Display order
    order = models.PositiveIntegerField(
        default=0,
        help_text="Display order within the paper"
    )

    class Meta:
        ordering = ['exam_paper', 'order', 'question_number']
        unique_together = ('exam_paper', 'question_number')

    def __str__(self):
        return f"{self.exam_paper} - Q{self.question_number}"

    # Timing is not stored: a question is worth half a minute per mark, so a
    # 30-mark question suggests 15 minutes and a 25-mark one 12.5. Questions
    # whose marks are not filled in yet return None, which hides the timer.
    @property
    def suggested_time_seconds(self):
        """Suggested time in seconds - exact, so 25 marks gives 12:30."""
        return self.total_marks * 30 if self.total_marks else None

    @property
    def suggested_time_minutes(self):
        """Suggested time in minutes, whole where it divides evenly."""
        if not self.total_marks:
            return None
        minutes = self.total_marks / 2
        return int(minutes) if minutes.is_integer() else minutes

    @property
    def suggested_time_display(self):
        """Suggested time as a m:ss clock, matching the countdown format."""
        seconds = self.suggested_time_seconds
        if not seconds:
            return None
        return f"{seconds // 60}:{seconds % 60:02d}"

    def clean(self):
        from django.core.exceptions import ValidationError
        errors = topic_errors(self.exam_paper if self.exam_paper_id else None,
                              self.topic, self.secondary_topic,
                              self.need_to_know_topic)
        if errors:
            raise ValidationError(errors)

    @property
    def topic_labels(self):
        """(label, topic) pairs for the topics set, main first."""
        labels = [('Main topic', self.topic),
                  ('Also covers', self.secondary_topic),
                  ('Need to know', self.need_to_know_topic)]
        return [(label, topic) for label, topic in labels if topic]

    @property
    def topic_slots(self):
        """(field, label, topic id) for each topic slot, for the editor."""
        return [('topic', 'Main topic', self.topic_id),
                ('secondary_topic', 'Secondary topic', self.secondary_topic_id),
                ('need_to_know_topic', 'Need to know', self.need_to_know_topic_id)]

    def get_retag_url(self):
        """Where the worksheet page posts this question's topics."""
        from django.urls import reverse
        return reverse('exam_papers:set_question_topics', args=[self.pk])

    @property
    def parts_with_schemes(self):
        """Parts that have at least one marking-scheme crop, in display order.

        Lets a template open a wrapper once, outside the loop. The old markup
        opened it on forloop.first, which stopped working the moment a part
        could carry more than one crop.
        """
        return [part for part in self.parts.all() if part.solution_images]

    def solution_images_status(self):
        """Returns a tuple of (parts_with_images, total_parts)"""
        total_parts = self.parts.count()
        parts_with_images = self.parts.filter(solution_image__isnull=False).exclude(solution_image='').count()
        return parts_with_images, total_parts

    @property
    def has_all_solution_images(self):
        """Returns True if all parts have solution images uploaded"""
        parts_with_images, total_parts = self.solution_images_status()
        return total_parts > 0 and parts_with_images == total_parts

    @property
    def solution_images_percentage(self):
        """Returns percentage of parts with solution images"""
        parts_with_images, total_parts = self.solution_images_status()
        if total_parts == 0:
            return 0
        return int((parts_with_images / total_parts) * 100)


class ExamQuestionPart(models.Model):
    """
    Represents a part of an exam question (e.g., part (a), (b), (c)).
    Uses marking scheme images for GPT-4 Vision-based grading.
    """
    question = models.ForeignKey(
        ExamQuestion,
        on_delete=models.CASCADE,
        related_name='parts'
    )

    # Part identification
    label = models.CharField(
        max_length=10,
        help_text="Part label (e.g., '(a)', '(b)', '(i)', '(ii)')"
    )

    # A part is a letter answered in one box, but on the paper (a) is often
    # (i) and (ii). The question image is the only other place that says so,
    # and students answered (i) alone and lost the marks for (ii).
    sub_parts = models.CharField(
        max_length=40,
        blank=True,
        help_text="Roman sub-parts this letter covers on the paper, comma-separated "
                  "(e.g. 'i,ii'). Filled from the scheme by fill_sub_parts; blank if none."
    )

    # Marking Scheme (replaces answer/solution fields)
    solution_image = models.ImageField(
        upload_to='exam_papers/marking_schemes/',
        blank=True,
        null=True,
        help_text="Marking scheme image - used by GPT-4 Vision for grading and extracting max marks"
    )

    # The one topic this part is filed under. Parts carried a set of topics for
    # a while, on the theory that (b) might draw on two; in practice not one
    # part in the database ever held two, and the tagging surface was too fine
    # to keep correct by hand. One majority topic is what a person can maintain.
    topic = models.ForeignKey(
        Topic,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='exam_question_parts',
        help_text="The topic carrying most of this part's marks"
    )

    # Marking (optional - auto-extracted from marking scheme if not set)
    max_marks = models.IntegerField(
        null=True,
        blank=True,
        help_text="Maximum marks for this part (leave blank to auto-extract from marking scheme image)"
    )

    # Solution access control
    solution_unlock_after_attempts = models.PositiveIntegerField(
        default=2,
        help_text="Number of attempts before marking scheme becomes visible (0 = always visible)"
    )

    # Display order
    order = models.PositiveIntegerField(
        default=0,
        help_text="Display order within the question"
    )

    class Meta:
        ordering = ['question', 'order']
        unique_together = ('question', 'label')

    def __str__(self):
        return f"{self.question} {self.label}"

    @property
    def solution_images(self):
        """This part's marking scheme as a list: its one image, or none.

        A part is a whole letter and its scheme is one image covering every
        (i), (ii) of it. The grader, the printable sheets and the PDFs take a
        list, which once held a crop per sub-part.
        """
        return [self.solution_image] if self.solution_image else []

    @property
    def sub_part_romans(self):
        """['i', 'ii'] for a part answered in a box per sub-part, else []."""
        romans = [r.strip() for r in self.sub_parts.split(',') if r.strip()]
        return romans if len(romans) >= 2 else []

    @property
    def sub_parts_display(self):
        """'(i) and (ii)', '(i), (ii) and (iii)' -- or '' for a plain letter."""
        labels = [f'({r})' for r in self.sub_part_romans]
        if not labels:
            return ''
        return ', '.join(labels[:-1]) + ' and ' + labels[-1]

    # The question page sends a box per sub-part as one answer, each piece
    # labelled \text{(i) } and so on: the shape the grader marks against the
    # scheme's sub-parts.
    _ANSWER_LABEL = re.compile(r'\\text\{\((i{1,3}|iv|vi{0,3}|ix|x)\) \}')

    def split_answer(self, answer):
        """A stored answer back into its sub-part boxes, as {roman: value}.

        An answer from before the boxes carries no labels, so it all goes in
        the first box rather than being lost.
        """
        romans = self.sub_part_romans
        if not romans or not answer:
            return {}
        pieces = self._ANSWER_LABEL.split(answer)
        if len(pieces) < 3:
            return {romans[0]: answer}
        values = {}
        for roman, value in zip(pieces[1::2], pieces[2::2]):
            value = value.strip()
            if value.endswith('\\quad'):
                value = value[:-len('\\quad')].rstrip()
            values[roman] = value
        return values

    @property
    def has_solution_image(self):
        """Returns True if solution image has been uploaded"""
        return bool(self.solution_image)




class ExamAttempt(models.Model):
    """
    Tracks a student's attempt at an exam paper.
    Can be a full paper attempt or individual question practice.
    """
    ATTEMPT_MODE_CHOICES = [
        ('full_timed', 'Full Paper - Timed'),
        ('full_practice', 'Full Paper - Practice'),
        ('question_practice', 'Individual Question Practice'),
    ]

    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='exam_attempts'
    )
    exam_paper = models.ForeignKey(
        ExamPaper,
        on_delete=models.CASCADE,
        related_name='attempts'
    )

    # Attempt metadata
    attempt_mode = models.CharField(
        max_length=20,
        choices=ATTEMPT_MODE_CHOICES,
        default='question_practice'
    )

    # Timing
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    time_spent_seconds = models.IntegerField(
        default=0,
        help_text="Total time spent on this attempt"
    )

    # Pause/Resume functionality
    is_paused = models.BooleanField(
        default=False,
        help_text="Whether the exam is currently paused"
    )
    paused_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the exam was paused"
    )
    total_paused_seconds = models.IntegerField(
        default=0,
        help_text="Total time the exam has been paused (to calculate accurate time remaining)"
    )
    last_seen_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the exam page last checked in; a longer silence counts as paused"
    )
    started_over_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Set when the student abandoned this attempt to start the paper again"
    )

    # Scoring
    total_marks_awarded = models.FloatField(default=0.0)
    total_marks_possible = models.FloatField(default=0.0)
    percentage_score = models.FloatField(default=0.0)

    # Status
    is_completed = models.BooleanField(default=False)
    is_submitted = models.BooleanField(
        default=False,
        help_text="True if student submitted the exam (for timed mode)"
    )

    class Meta:
        ordering = ['-started_at']

    def __str__(self):
        return f"{self.student.username} - {self.exam_paper} ({self.started_at.strftime('%Y-%m-%d')})"

    # The timed exam page checks in every 30 seconds while it is open. A
    # silence longer than this means the student left without pausing --
    # closed the tab, shut the laptop, locked the phone -- and the gap is
    # treated as paused, so Resume picks up with the time they had left.
    AWAY_AFTER = timedelta(minutes=2)

    def note_presence(self, now=None):
        """Record that the exam page is open, crediting any absence as paused."""
        if self.attempt_mode != 'full_timed' or self.is_completed:
            return
        now = now or timezone.now()
        if (not self.is_paused and self.last_seen_at
                and now - self.last_seen_at > self.AWAY_AFTER):
            self.total_paused_seconds += int((now - self.last_seen_at).total_seconds())
        self.last_seen_at = now
        self.save(update_fields=['total_paused_seconds', 'last_seen_at'])

    def time_remaining_seconds(self, now=None):
        """Seconds left on a timed attempt, not counting paused or away time."""
        now = now or timezone.now()
        end = now
        if self.is_paused and self.paused_at:
            end = self.paused_at
        elif self.last_seen_at and now - self.last_seen_at > self.AWAY_AFTER:
            # Away and not yet back: the clock stopped when the page went quiet
            end = self.last_seen_at
        elapsed = (end - self.started_at).total_seconds() - self.total_paused_seconds
        return int(max(0, self.exam_paper.time_limit_minutes * 60 - elapsed))

    def calculate_score(self):
        """Calculate total score from all question attempts"""
        question_attempts = self.question_attempts.all()
        self.total_marks_awarded = sum(qa.marks_awarded for qa in question_attempts)
        self.total_marks_possible = sum(qa.max_marks for qa in question_attempts)

        if self.total_marks_possible > 0:
            self.percentage_score = (self.total_marks_awarded / self.total_marks_possible) * 100
        else:
            self.percentage_score = 0.0

        self.save()


class ExamQuestionAttempt(models.Model):
    """
    Tracks a student's attempt at a specific exam question part.
    Multiple attempts can exist for practice mode.
    """
    exam_attempt = models.ForeignKey(
        ExamAttempt,
        on_delete=models.CASCADE,
        related_name='question_attempts'
    )
    question_part = models.ForeignKey(
        ExamQuestionPart,
        on_delete=models.CASCADE,
        related_name='attempts'
    )

    # Student's answer
    student_answer = models.TextField(blank=True)

    # Grading
    marks_awarded = models.FloatField(default=0.0)
    max_marks = models.IntegerField()
    is_correct = models.BooleanField(default=False)
    feedback = models.TextField(
        blank=True,
        help_text="Automated or manual feedback"
    )

    # Attempt metadata
    attempt_number = models.PositiveIntegerField(
        default=1,
        help_text="Which attempt is this (1st, 2nd, 3rd, etc.)"
    )
    time_spent_seconds = models.IntegerField(
        default=0,
        help_text="Time spent on this specific question part"
    )

    # Help usage tracking
    hint_used = models.BooleanField(default=False)
    solution_viewed = models.BooleanField(default=False)

    # Timestamps
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-submitted_at']

    def __str__(self):
        return f"{self.exam_attempt.student.username} - {self.question_part} (Attempt {self.attempt_number})"


class ExamQuestionFeedback(models.Model):
    """Track student feedback (thumbs up/down) on exam question grading/feedback."""
    FEEDBACK_CHOICES = [
        ('helpful', 'Thumbs Up'),
        ('not_helpful', 'Thumbs Down'),
    ]

    attempt = models.ForeignKey(
        ExamQuestionAttempt,
        on_delete=models.CASCADE,
        related_name='feedback_responses',
        help_text="The exam question attempt this feedback is for"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='exam_question_feedback',
        help_text="Student who provided feedback"
    )
    feedback_type = models.CharField(
        max_length=20,
        choices=FEEDBACK_CHOICES,
        help_text="Whether student found feedback helpful or not"
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ['attempt', 'user']
        verbose_name = 'Exam Question Feedback'
        verbose_name_plural = 'Exam Question Feedback'

    def __str__(self):
        return f"{self.user.username} - {self.get_feedback_type_display()} - Attempt {self.attempt.id}"

class TeacherExam(models.Model):
    """An exam a teacher puts together from past exam questions, to print.

    Owned by the teacher who made it and seen by no one else. The questions are
    shared ExamQuestion rows, so a retag or a better crop reaches every exam
    that uses them.
    """
    DEFAULT_INSTRUCTIONS = (
        'Answer all questions.\n'
        'Write your answers in the spaces provided.\n'
        'Show all necessary work clearly. Marks may be lost if you do not.\n'
        'The Formulae and Tables booklet may be used.'
    )

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='teacher_exams')
    subject = models.ForeignKey('core.Subject', on_delete=models.CASCADE,
                                related_name='teacher_exams')
    title = models.CharField(max_length=120, help_text='e.g. Christmas Exam 2026')
    subtitle = models.CharField(max_length=120, blank=True,
                                help_text='School, class or level, e.g. 6th Year Higher Level')
    exam_date = models.DateField(null=True, blank=True)
    duration_minutes = models.PositiveIntegerField(null=True, blank=True,
                                                   help_text='Time allowed')
    instructions = models.TextField(blank=True, default=DEFAULT_INSTRUCTIONS)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return self.title

    def ordered_items(self):
        return self.items.select_related(
            'question__exam_paper', 'question__topic').prefetch_related(
            'question__parts', 'omitted_parts').order_by('order', 'id')

    @property
    def total_marks(self):
        return sum(item.marks for item in self.ordered_items())


class TeacherExamQuestion(models.Model):
    """One past question in a teacher's exam, at its place in the running order."""
    exam = models.ForeignKey(TeacherExam, on_delete=models.CASCADE, related_name='items')
    question = models.ForeignKey(ExamQuestion, on_delete=models.CASCADE,
                                 related_name='teacher_exam_items')
    order = models.PositiveIntegerField(default=0)
    # Parts the teacher has told students not to answer, e.g. (c) of a long
    # question in a short exam. They come off the question's marks, the paper
    # tells students to skip them, and the marking scheme leaves them out.
    omitted_parts = models.ManyToManyField(ExamQuestionPart, blank=True,
                                           related_name='omitted_from_teacher_exams')

    class Meta:
        ordering = ['order', 'id']
        unique_together = ('exam', 'question')

    def __str__(self):
        return f'{self.exam} - {self.question}'

    def omitted(self):
        """The left-out parts, in the question's order."""
        return sorted(self.omitted_parts.all(), key=lambda part: (part.order, part.id))

    @property
    def marks(self):
        """The question's marks less any parts left out."""
        left_out = sum(part.max_marks or 0 for part in self.omitted_parts.all())
        return max(0, question_marks(self.question) - left_out)

    @property
    def skip_note(self):
        """'Do not answer part (c).' for the paper, or '' when nothing is left out."""
        labels = [part.label for part in self.omitted()]
        if not labels:
            return ''
        if len(labels) == 1:
            return f'Do not answer part {labels[0]}.'
        return f'Do not answer parts {", ".join(labels[:-1])} and {labels[-1]}.'


def question_marks(question):
    """A question's marks, or its parts' when the total was never filled in.

    Some questions carry total_marks = 0 with the marks on their parts.
    """
    if question.total_marks:
        return question.total_marks
    return sum(part.max_marks or 0 for part in question.parts.all())


def script_page_path(instance, filename):
    # Served only through a view that checks the exam's owner; random names
    # anyway, as homework_check does, so nothing here is guessable.
    return f'exam_scripts/{instance.script_id}/{uuid.uuid4().hex}.jpg'


class ExamScript(models.Model):
    """One student's answered paper for a teacher's exam, scanned in.

    Students write on the printed paper, so page n of the scan is page n of
    the exam and each question's pages are known without reading anything.
    The pages are student work: kept in private storage, served only to the
    exam's owner, never shown to the student.
    """
    exam = models.ForeignKey(TeacherExam, on_delete=models.CASCADE, related_name='scripts')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='exam_scripts')
    page_count = models.PositiveSmallIntegerField(default=0)
    # The page count the exam's PDF had when the scan came in. A mismatch means
    # the pages cannot be lined up by number and the teacher sets them by hand.
    expected_pages = models.PositiveSmallIntegerField(default=0)
    reviewed_at = models.DateTimeField(null=True, blank=True,
                                       help_text='When the teacher confirmed the marks')
    teacher_comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['student__last_name', 'student__first_name', 'student__username']
        unique_together = ('exam', 'student')

    def __str__(self):
        return f'{self.exam} - {self.student.username}'

    @property
    def pages_line_up(self):
        return self.page_count == self.expected_pages

    def ordered_questions(self):
        return self.questions.select_related('item__question').prefetch_related(
            'marks__part').order_by('item__order', 'item__id')

    @property
    def total(self):
        """(awarded, possible); awarded is None while any part is unmarked."""
        awarded, possible = 0, 0
        for question in self.ordered_questions():
            got, out_of = question.total
            possible += out_of
            awarded = None if awarded is None or got is None else awarded + got
        return awarded, possible


class ExamScriptPage(models.Model):
    script = models.ForeignKey(ExamScript, on_delete=models.CASCADE, related_name='pages')
    number = models.PositiveSmallIntegerField(help_text='1 for the cover')
    image = models.ImageField(upload_to=script_page_path, storage=private_storage)

    class Meta:
        ordering = ['number']
        unique_together = ('script', 'number')


class ExamScriptQuestion(models.Model):
    """One question of one script: which pages it is on, and how marking went."""
    PENDING, MARKED, FAILED = 'pending', 'marked', 'failed'
    STATUS_CHOICES = [(PENDING, 'Not marked yet'), (MARKED, 'Marked'), (FAILED, 'Could not be marked')]

    script = models.ForeignKey(ExamScript, on_delete=models.CASCADE, related_name='questions')
    item = models.ForeignKey(TeacherExamQuestion, on_delete=models.CASCADE,
                             related_name='script_questions')
    first_page = models.PositiveSmallIntegerField(null=True, blank=True)
    last_page = models.PositiveSmallIntegerField(null=True, blank=True)
    status = models.CharField(max_length=8, choices=STATUS_CHOICES, default=PENDING)
    message = models.CharField(max_length=300, blank=True,
                               help_text='Why it could not be marked, in words for the teacher')
    model_used = models.CharField(max_length=64, blank=True)
    prompt_tokens = models.PositiveIntegerField(default=0)
    completion_tokens = models.PositiveIntegerField(default=0)
    marked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['item__order', 'item__id']
        unique_together = ('script', 'item')

    def page_numbers(self):
        if not self.first_page or not self.last_page:
            return []
        return list(range(self.first_page, self.last_page + 1))

    @property
    def total(self):
        """(awarded, possible) over this question's marks rows."""
        marks = list(self.marks.all())
        possible = sum(mark.max_marks for mark in marks)
        if any(mark.final is None for mark in marks) or not marks:
            return None, possible
        return sum(mark.final for mark in marks), possible


class ExamScriptMark(models.Model):
    """The mark for one part of one question on one script.

    part is empty for a question marked as a whole: one whose parts carry no
    marks of their own, so only the question's total is known.
    """
    question = models.ForeignKey(ExamScriptQuestion, on_delete=models.CASCADE,
                                 related_name='marks')
    part = models.ForeignKey(ExamQuestionPart, on_delete=models.CASCADE, null=True, blank=True)
    label = models.CharField(max_length=20)
    max_marks = models.PositiveSmallIntegerField()
    ai_mark = models.PositiveSmallIntegerField(null=True, blank=True)
    teacher_mark = models.PositiveSmallIntegerField(null=True, blank=True)
    transcription = models.TextField(blank=True)
    reasoning = models.TextField(blank=True)
    feedback = models.TextField(blank=True)
    confidence = models.CharField(max_length=8, blank=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    @property
    def final(self):
        """The teacher's mark if they gave one, otherwise the marker's."""
        return self.teacher_mark if self.teacher_mark is not None else self.ai_mark
