"""What a checkpoint is worth: which work counts, what help costs, and why a
result once earned never changes afterwards."""
from datetime import timedelta

from django.contrib.auth.models import Group, User
from django.test import TestCase, override_settings
from django.utils import timezone

from core.models import Subject
from exam_papers.models import (
    ExamAttempt, ExamPaper, ExamQuestion, ExamQuestionAttempt, ExamQuestionPart,
)
from homework.models import TeacherProfile
from interactive_lessons.models import Topic
from students.models import WorkSubmission
from studyplans.models import StudyPlan, StudyPlanGoal
from studyplans.services import checkpoints


def make_teacher(username):
    user = User.objects.create_user(username=username, password='pw', is_staff=True)
    group, _ = Group.objects.get_or_create(name='Teachers')
    user.groups.add(group)
    profile, _ = TeacherProfile.objects.get_or_create(user=user)
    return user, profile


class CheckpointTestBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.maths = Subject.objects.get(slug='maths')
        cls.topic = Topic.objects.create(
            name='Integration', subject=cls.maths, paper='p1')

        cls.teacher_user, cls.teacher = make_teacher('ms_teacher')
        cls.student = User.objects.create_user('aoife', password='pw')

        cls.paper = ExamPaper.objects.create(
            subject=cls.maths, year=2019, paper_type='p1',
            total_marks=300, is_published=True)
        cls.question = ExamQuestion.objects.create(
            exam_paper=cls.paper, question_number=6,
            topic=cls.topic, total_marks=30)
        cls.part_a = ExamQuestionPart.objects.create(
            question=cls.question, label='(a)', max_marks=10, order=1)
        cls.part_b = ExamQuestionPart.objects.create(
            question=cls.question, label='(b)', max_marks=20, order=2)
        for part in (cls.part_a, cls.part_b):
            part.topic = cls.topic
            part.save(update_fields=['topic'])

        cls.today = timezone.localdate()
        cls.plan = StudyPlan.objects.create(
            student=cls.student, teacher=cls.teacher, subject=cls.maths,
            title='Christmas Push', start_date=cls.today,
            deadline=cls.today + timedelta(days=28), status='active')
        cls.goal = StudyPlanGoal.objects.create(
            plan=cls.plan, topic=cls.topic, target_mastery=75, checkpoint_size=2)

    def attempt(self, part, marks, *, max_marks=None, when=None,
                hint=False, solution=False):
        """One graded attempt, with submitted_at forced past auto_now_add."""
        exam_attempt, _ = ExamAttempt.objects.get_or_create(
            student=self.student, exam_paper=self.paper,
            attempt_mode='question_practice')
        row = ExamQuestionAttempt.objects.create(
            exam_attempt=exam_attempt, question_part=part,
            student_answer='x', marks_awarded=marks,
            max_marks=max_marks if max_marks is not None else (part.max_marks or 10),
            hint_used=hint, solution_viewed=solution)
        if when is not None:
            ExamQuestionAttempt.objects.filter(pk=row.pk).update(submitted_at=when)
            row.refresh_from_db()
        return row

    def ready_checkpoint(self, unlocked_at=None):
        cp = checkpoints.create_checkpoint(
            self.goal, parts=[self.part_a, self.part_b], status='ready')
        if unlocked_at is not None:
            cp.unlocked_at = unlocked_at
            cp.save(update_fields=['unlocked_at'])
        return cp


class CheckpointScoringTests(CheckpointTestBase):

    def test_score_is_marks_awarded_over_marks_available(self):
        cp = self.ready_checkpoint()
        self.attempt(self.part_a, 8)    # 8/10
        self.attempt(self.part_b, 16)   # 16/20
        checkpoints.grade(cp)
        cp.refresh_from_db()
        self.assertEqual(cp.marks_awarded, 24.0)
        self.assertEqual(cp.marks_possible, 30.0)
        self.assertEqual(cp.score, 80.0)
        self.assertEqual(cp.status, 'passed')

    def test_a_score_exactly_on_the_pass_mark_passes(self):
        cp = self.ready_checkpoint()
        self.attempt(self.part_a, 7.5)
        self.attempt(self.part_b, 15)
        checkpoints.grade(cp)
        cp.refresh_from_db()
        self.assertEqual(cp.score, 75.0)
        self.assertEqual(cp.status, 'passed')

    def test_falling_short_of_the_pass_mark_fails(self):
        cp = self.ready_checkpoint()
        self.attempt(self.part_a, 5)
        self.attempt(self.part_b, 10)
        checkpoints.grade(cp)
        cp.refresh_from_db()
        self.assertEqual(cp.score, 50.0)
        self.assertEqual(cp.status, 'failed')

    def test_work_done_before_the_checkpoint_opened_does_not_count(self):
        """The guard against a checkpoint marking itself from old work."""
        opened = timezone.now()
        cp = self.ready_checkpoint(unlocked_at=opened)
        self.attempt(self.part_a, 10, when=opened - timedelta(days=3))
        self.attempt(self.part_b, 20, when=opened - timedelta(days=3))

        checkpoints.grade(cp)
        cp.refresh_from_db()
        self.assertEqual(cp.status, 'ready', "old attempts should not sit it")
        self.assertIsNone(cp.score)
        self.assertFalse(checkpoints.is_sat(cp))

    def test_the_best_attempt_in_the_window_is_the_one_that_counts(self):
        cp = self.ready_checkpoint()
        self.attempt(self.part_a, 3)
        self.attempt(self.part_a, 9)
        self.attempt(self.part_b, 20)
        checkpoints.grade(cp)
        cp.refresh_from_db()
        self.assertEqual(cp.marks_awarded, 29.0)

    def test_a_part_the_student_never_sat_leaves_the_checkpoint_unmarked(self):
        cp = self.ready_checkpoint()
        self.attempt(self.part_a, 10)
        checkpoints.grade(cp)
        cp.refresh_from_db()
        self.assertEqual(cp.status, 'ready')

    def test_it_uses_the_attempts_own_max_marks_when_the_part_has_none(self):
        """ExamQuestionPart.max_marks is nullable; the attempt's copy is not."""
        self.part_a.max_marks = None
        self.part_a.save(update_fields=['max_marks'])
        cp = checkpoints.create_checkpoint(
            self.goal, parts=[self.part_a], status='ready')
        self.attempt(self.part_a, 6, max_marks=12)  # 50%
        checkpoints.grade(cp)
        cp.refresh_from_db()
        self.assertEqual(cp.score, 50.0)


class CheckpointHelpPenaltyTests(CheckpointTestBase):

    def test_a_hint_costs_twenty_percent(self):
        cp = checkpoints.create_checkpoint(
            self.goal, parts=[self.part_a], status='ready')
        self.attempt(self.part_a, 10, hint=True)
        checkpoints.grade(cp)
        cp.refresh_from_db()
        self.assertEqual(cp.score, 80.0)
        self.assertTrue(cp.is_clean, "a hint is not a marking scheme")

    def test_opening_the_marking_scheme_costs_half_and_marks_it_unclean(self):
        cp = checkpoints.create_checkpoint(
            self.goal, parts=[self.part_a], status='ready')
        self.attempt(self.part_a, 10, solution=True)
        checkpoints.grade(cp)
        cp.refresh_from_db()
        self.assertEqual(cp.score, 50.0)
        self.assertFalse(cp.is_clean)

    def test_help_taken_on_any_attempt_taints_the_whole_part(self):
        """The flag lands on the attempt before the one it influenced."""
        cp = checkpoints.create_checkpoint(
            self.goal, parts=[self.part_a], status='ready')
        self.attempt(self.part_a, 2, solution=True)   # then they looked
        self.attempt(self.part_a, 10)                 # and got it right after
        checkpoints.grade(cp)
        cp.refresh_from_db()
        self.assertEqual(cp.score, 50.0, "the later attempt is tainted too")
        self.assertFalse(cp.is_clean)


class CheckpointRecordTests(CheckpointTestBase):

    def test_the_pass_mark_is_frozen_when_the_checkpoint_is_set(self):
        cp = self.ready_checkpoint()
        self.goal.target_mastery = 95
        self.goal.save(update_fields=['target_mastery'])
        cp.refresh_from_db()
        self.assertEqual(cp.pass_mark, 75,
                         "raising the target must not reach back in time")

    def test_marks_possible_is_frozen_against_later_edits(self):
        cp = self.ready_checkpoint()
        self.part_a.max_marks = 999
        self.part_a.save(update_fields=['max_marks'])
        part = cp.parts.get(exam_question_part=self.part_a)
        self.assertEqual(part.marks_possible, 10)

    def test_the_result_is_written_onto_each_part(self):
        cp = self.ready_checkpoint()
        self.attempt(self.part_a, 8)
        self.attempt(self.part_b, 16)
        checkpoints.grade(cp)
        part = cp.parts.get(exam_question_part=self.part_a)
        self.assertEqual(part.marks_awarded, 8.0)
        self.assertEqual(part.score, 80.0)
        self.assertIsNotNone(part.attempted_at)

    def test_marking_a_decided_checkpoint_again_changes_nothing(self):
        cp = self.ready_checkpoint()
        self.attempt(self.part_a, 8)
        self.attempt(self.part_b, 16)
        checkpoints.grade(cp)
        cp.refresh_from_db()
        first_sat_at, first_score = cp.sat_at, cp.score

        self.attempt(self.part_a, 10)
        checkpoints.grade(cp)
        cp.refresh_from_db()
        self.assertEqual(cp.sat_at, first_sat_at)
        self.assertEqual(cp.score, first_score)

    def test_a_pass_is_copied_onto_the_goal(self):
        cp = self.ready_checkpoint()
        self.attempt(self.part_a, 9)
        self.attempt(self.part_b, 18)
        checkpoints.grade(cp)
        checkpoints.record_result(cp)
        self.goal.refresh_from_db()
        self.assertIsNotNone(self.goal.mastered_at)
        self.assertEqual(self.goal.mastery_score, 90.0)
        self.assertTrue(self.goal.is_mastered)

    def test_a_fail_leaves_the_goal_unmastered(self):
        cp = self.ready_checkpoint()
        self.attempt(self.part_a, 1)
        self.attempt(self.part_b, 2)
        checkpoints.grade(cp)
        checkpoints.record_result(cp)
        self.goal.refresh_from_db()
        self.assertIsNone(self.goal.mastered_at)
        self.assertFalse(self.goal.is_mastered)


class WhichCheckpointCountsTests(CheckpointTestBase):
    """Retries are reserved in advance, so the highest round number is normally
    a locked future one. Picking that would hide a checkpoint waiting to be sat."""

    def setUp(self):
        # Round 1 open, rounds 2 and 3 held back -- what the planner produces.
        self.round1 = checkpoints.create_checkpoint(
            self.goal, parts=[self.part_a], round_number=1, status='ready')
        self.round2 = checkpoints.create_checkpoint(
            self.goal, parts=[self.part_b], round_number=2, status='locked')

    def test_a_checkpoint_waiting_to_be_sat_is_the_one_that_counts(self):
        self.assertEqual(self.goal.current_checkpoint(), self.round1)

    def test_the_progress_card_says_ready_not_working(self):
        from studyplans.services import progress
        state = progress.goal_state(self.goal)
        self.assertEqual(state['state'], 'ready')
        self.assertEqual(state['checkpoint'], self.round1)

    def test_once_decided_the_result_is_what_counts(self):
        self.attempt(self.part_a, 1)
        checkpoints.grade(self.round1)
        self.round1.refresh_from_db()
        self.assertEqual(self.round1.status, 'failed')
        self.assertEqual(self.goal.current_checkpoint(), self.round1)

    def test_a_reopened_retry_takes_over(self):
        self.attempt(self.part_a, 1)
        checkpoints.grade(self.round1)
        checkpoints.unlock(self.round2)
        self.assertEqual(self.goal.current_checkpoint(), self.round2)

    def test_with_nothing_open_the_next_locked_round_is_shown(self):
        self.round1.status = 'locked'
        self.round1.unlocked_at = None
        self.round1.save(update_fields=['status', 'unlocked_at'])
        self.assertEqual(self.goal.current_checkpoint(), self.round1)


class PhotoTestBase(CheckpointTestBase):

    def photo(self, part, mark, *, out_of=None, when=None,
              status=WorkSubmission.Status.COMPLETE):
        row = WorkSubmission.objects.create(
            student=self.student.studentprofile, exam_question_part=part,
            status=status, estimated_mark=mark,
            estimated_max_marks=out_of or part.max_marks)
        if when is not None:
            WorkSubmission.objects.filter(pk=row.pk).update(created_at=when)
        return row


class PhotoMarkTests(PhotoTestBase):
    """A "show that" cannot be typed, so with the setting on a photo of the
    working can carry a part -- only ever for the better, and only where the
    analysis was willing to give a mark at all."""

    @override_settings(WORK_PHOTO_COUNTS_ON_CHECKPOINTS=False)
    def test_off_by_default_a_photo_counts_for_nothing(self):
        cp = self.ready_checkpoint()
        self.attempt(self.part_a, 10)
        self.photo(self.part_b, 20)
        self.assertFalse(checkpoints.is_sat(cp))
        checkpoints.grade(cp)
        cp.refresh_from_db()
        self.assertEqual(cp.status, 'ready')

    @override_settings(WORK_PHOTO_COUNTS_ON_CHECKPOINTS=True)
    def test_a_photo_can_answer_a_part_on_its_own(self):
        cp = self.ready_checkpoint()
        self.attempt(self.part_a, 10)
        self.photo(self.part_b, 18)
        checkpoints.grade(cp)
        cp.refresh_from_db()
        self.assertEqual((cp.marks_awarded, cp.status), (28.0, 'passed'))
        part = cp.parts.get(exam_question_part=self.part_b)
        self.assertTrue(part.marked_from_photo)

    @override_settings(WORK_PHOTO_COUNTS_ON_CHECKPOINTS=True)
    def test_the_better_of_typed_and_photo_counts(self):
        cp = self.ready_checkpoint()
        self.attempt(self.part_a, 10)
        self.attempt(self.part_b, 5)      # typed only the final value
        self.photo(self.part_b, 17)       # the working earns the rest
        checkpoints.grade(cp)
        cp.refresh_from_db()
        self.assertEqual(cp.marks_awarded, 27.0)

    @override_settings(WORK_PHOTO_COUNTS_ON_CHECKPOINTS=True)
    def test_a_worse_photo_does_not_drag_a_typed_mark_down(self):
        cp = self.ready_checkpoint()
        self.attempt(self.part_a, 10)
        self.attempt(self.part_b, 18)
        self.photo(self.part_b, 4)
        checkpoints.grade(cp)
        part = cp.parts.get(exam_question_part=self.part_b)
        self.assertEqual(part.marks_awarded, 18.0)
        self.assertFalse(part.marked_from_photo)

    @override_settings(WORK_PHOTO_COUNTS_ON_CHECKPOINTS=True)
    def test_a_photo_with_its_mark_withheld_does_not_count(self):
        cp = self.ready_checkpoint()
        self.attempt(self.part_a, 10)
        self.photo(self.part_b, None)
        self.assertFalse(checkpoints.is_sat(cp))

    @override_settings(WORK_PHOTO_COUNTS_ON_CHECKPOINTS=True)
    def test_a_photo_still_being_analysed_does_not_count(self):
        cp = self.ready_checkpoint()
        self.attempt(self.part_a, 10)
        self.photo(self.part_b, 20, status=WorkSubmission.Status.ANALYSING)
        self.assertFalse(checkpoints.is_sat(cp))

    @override_settings(WORK_PHOTO_COUNTS_ON_CHECKPOINTS=True)
    def test_a_photo_from_before_it_opened_does_not_count(self):
        cp = self.ready_checkpoint()
        self.attempt(self.part_a, 10)
        self.photo(self.part_b, 20, when=cp.unlocked_at - timedelta(days=1))
        self.assertFalse(checkpoints.is_sat(cp))

    @override_settings(WORK_PHOTO_COUNTS_ON_CHECKPOINTS=True)
    def test_opening_the_scheme_still_costs_half_on_a_photo(self):
        cp = self.ready_checkpoint()
        self.attempt(self.part_a, 10)
        self.attempt(self.part_b, 0, solution=True)
        self.photo(self.part_b, 20)
        checkpoints.grade(cp)
        part = cp.parts.get(exam_question_part=self.part_b)
        self.assertEqual(part.marks_awarded, 10.0)
        cp.refresh_from_db()
        self.assertFalse(cp.is_clean)


class PhotoMarkLabelTests(PhotoTestBase):
    """The words beside a photo's mark must never promise more than grading does."""

    def label(self, photo):
        from students.views_work import _mark_label
        return _mark_label(photo)

    @override_settings(WORK_PHOTO_COUNTS_ON_CHECKPOINTS=True)
    def test_on_an_open_badge_test_part_it_says_it_counts(self):
        cp = self.ready_checkpoint()
        photo = self.photo(self.part_b, 12)
        self.assertEqual(checkpoints.badge_test_counting_photo(photo), cp)
        self.assertIn('counts on your Integration Badge Test', self.label(photo))

    @override_settings(WORK_PHOTO_COUNTS_ON_CHECKPOINTS=False)
    def test_with_the_setting_off_it_is_only_a_guide(self):
        self.ready_checkpoint()
        photo = self.photo(self.part_b, 12)
        self.assertIn('a guide, not an official mark', self.label(photo))

    @override_settings(WORK_PHOTO_COUNTS_ON_CHECKPOINTS=True)
    def test_a_part_on_no_open_badge_test_is_only_a_guide(self):
        checkpoints.create_checkpoint(
            self.goal, parts=[self.part_a, self.part_b], status='locked')
        photo = self.photo(self.part_b, 12)
        self.assertIn('a guide', self.label(photo))

    @override_settings(WORK_PHOTO_COUNTS_ON_CHECKPOINTS=True)
    def test_a_photo_from_before_it_opened_is_only_a_guide(self):
        cp = self.ready_checkpoint()
        photo = self.photo(self.part_b, 12, when=cp.unlocked_at - timedelta(days=1))
        photo.refresh_from_db()
        self.assertIn('a guide', self.label(photo))

    @override_settings(WORK_PHOTO_COUNTS_ON_CHECKPOINTS=True)
    def test_no_mark_means_no_label(self):
        self.ready_checkpoint()
        self.assertEqual(self.label(self.photo(self.part_b, None)), '')
