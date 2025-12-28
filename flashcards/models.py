from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from interactive_lessons.models import Topic
import random


class FlashcardSet(models.Model):
    """
    A collection of flashcards grouped by topic.
    Similar to QuickKick and CheatSheet patterns - simple container linked to Topic.
    """
    topic = models.ForeignKey(
        Topic,
        on_delete=models.CASCADE,
        related_name="flashcard_sets",
        help_text="Topic this flashcard set belongs to"
    )
    title = models.CharField(
        max_length=200,
        help_text="Display title (e.g., 'Trigonometry Identities', 'Differentiation Rules')"
    )
    description = models.TextField(
        blank=True,
        help_text="Brief overview of what this set covers"
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text="Display order within topic"
    )
    is_published = models.BooleanField(
        default=False,
        help_text="Make visible to students (draft mode if False)"
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_flashcard_sets'
    )

    class Meta:
        ordering = ('topic', 'order', 'title')
        verbose_name = "Flashcard Set"
        verbose_name_plural = "Flashcard Sets"

    def __str__(self):
        return f"{self.topic.name} - {self.title}"

    def card_count(self):
        """Return number of cards in this set"""
        return self.cards.count()


class Flashcard(models.Model):
    """
    Individual flashcard with rich content on both sides.
    Follows RevisionSection pattern for content storage.
    """
    flashcard_set = models.ForeignKey(
        FlashcardSet,
        on_delete=models.CASCADE,
        related_name="cards",
        help_text="Set this card belongs to"
    )

    # FRONT SIDE - Question/Prompt
    front_text = models.TextField(
        help_text="Front content - supports Markdown and LaTeX (use $...$ for inline, $$...$$ for display)"
    )
    front_image = models.ImageField(
        upload_to='flashcards/front/',
        blank=True,
        null=True,
        help_text="Optional image for front of card"
    )

    # BACK SIDE - Correct Answer
    back_text = models.TextField(
        help_text="Correct answer text - supports Markdown and LaTeX"
    )
    back_image = models.ImageField(
        upload_to='flashcards/back/',
        blank=True,
        null=True,
        help_text="Optional image for back of card (e.g., diagram, worked solution)"
    )

    # MULTIPLE CHOICE OPTIONS
    distractor_1 = models.TextField(
        help_text="First incorrect option - supports Markdown and LaTeX"
    )
    distractor_2 = models.TextField(
        help_text="Second incorrect option - supports Markdown and LaTeX"
    )
    distractor_3 = models.TextField(
        help_text="Third incorrect option - supports Markdown and LaTeX"
    )

    # Optional explanation shown after answer
    explanation = models.TextField(
        blank=True,
        help_text="Optional explanation shown after answering (why answer is correct)"
    )

    # Ordering
    order = models.PositiveIntegerField(
        default=0,
        help_text="Display order within set"
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('flashcard_set', 'order')
        verbose_name = "Flashcard"
        verbose_name_plural = "Flashcards"

    def __str__(self):
        preview = self.front_text[:50]
        if len(self.front_text) > 50:
            preview += "..."
        return f"{self.flashcard_set.title} - Card {self.order}: {preview}"

    def get_shuffled_options(self):
        """
        Return list of all 4 options shuffled, with correct answer marked.
        Returns: list of dicts with 'text' and 'is_correct' keys
        """
        options = [
            {'text': self.back_text, 'is_correct': True, 'id': 'correct'},
            {'text': self.distractor_1, 'is_correct': False, 'id': 'dist1'},
            {'text': self.distractor_2, 'is_correct': False, 'id': 'dist2'},
            {'text': self.distractor_3, 'is_correct': False, 'id': 'dist3'},
        ]
        random.shuffle(options)
        return options


class FlashcardAttempt(models.Model):
    """
    Tracks student interactions with flashcards.
    Follows QuestionAttempt pattern with mastery level tracking.
    """
    MASTERY_CHOICES = [
        ('new', 'New (Never Seen)'),
        ('learning', 'Learning'),
        ('know', 'Know'),
        ('dont_know', "Don't Know"),
    ]

    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='flashcard_attempts',
        limit_choices_to={'is_staff': False}
    )
    flashcard = models.ForeignKey(
        Flashcard,
        on_delete=models.CASCADE,
        related_name='attempts'
    )

    # Progress tracking
    view_count = models.PositiveIntegerField(
        default=0,
        help_text="How many times student has viewed this card"
    )
    correct_count = models.PositiveIntegerField(
        default=0,
        help_text="How many times answered correctly"
    )
    incorrect_count = models.PositiveIntegerField(
        default=0,
        help_text="How many times answered incorrectly"
    )

    # Mastery state
    mastery_level = models.CharField(
        max_length=20,
        choices=MASTERY_CHOICES,
        default='new',
        help_text="Current mastery state for this card"
    )

    # Last interaction tracking
    last_viewed_at = models.DateTimeField(
        auto_now=True,
        help_text="Last time student viewed this card"
    )
    last_answered_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last time student answered this card"
    )
    last_answer_correct = models.BooleanField(
        null=True,
        blank=True,
        help_text="Was the last answer correct?"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'flashcard')
        ordering = ['-last_viewed_at']
        verbose_name = "Flashcard Attempt"
        verbose_name_plural = "Flashcard Attempts"

    def __str__(self):
        return f"{self.student.username} - {self.flashcard} ({self.mastery_level})"

    def record_view(self):
        """Increment view count"""
        self.view_count += 1
        self.save(update_fields=['view_count', 'last_viewed_at'])

    def record_answer(self, is_correct):
        """
        Record an answer and update mastery level based on transition logic.

        Mastery Transition Logic:
        - new -> learning (first correct) or dont_know (first incorrect)
        - learning -> know (if correct)
        - learning -> dont_know (if multiple incorrect)
        - know -> learning (if incorrect, needs review)
        - dont_know -> learning (if correct, showing improvement)
        """
        # Update counts
        if is_correct:
            self.correct_count += 1
        else:
            self.incorrect_count += 1

        # Update mastery state based on current state and result
        if self.mastery_level == 'new':
            # First attempt - move to learning or dont_know
            self.mastery_level = 'learning' if is_correct else 'dont_know'

        elif self.mastery_level == 'learning':
            # In learning phase
            if is_correct:
                # Correct answer promotes to 'know'
                self.mastery_level = 'know'
            else:
                # Multiple incorrect demotes to dont_know
                if self.incorrect_count >= 2:
                    self.mastery_level = 'dont_know'

        elif self.mastery_level == 'know':
            # Already mastered - incorrect answer demotes to learning
            if not is_correct:
                self.mastery_level = 'learning'
            # Stays 'know' if correct

        elif self.mastery_level == 'dont_know':
            # Struggling - correct answer promotes back to learning
            if is_correct:
                self.mastery_level = 'learning'
            # Stays dont_know if incorrect

        # Update timestamps
        self.last_answer_correct = is_correct
        self.last_answered_at = timezone.now()

        self.save()
