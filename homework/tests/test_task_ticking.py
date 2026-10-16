"""A student ticks off a written exercise by hand; every other task completes
itself from what they did on the site, so it cannot be ticked without doing it."""
from django.urls import reverse

from homework.models import HomeworkTask, StudentHomeworkProgress
from homework.tests.test_exam_part_tasks import ExamPartTaskTestBase


class TaskTickingTests(ExamPartTaskTestBase):
    def progress_for(self, task):
        return StudentHomeworkProgress.objects.create(
            student=self.student, assignment=self.assignment, task=task)

    def toggle(self, progress):
        self.client.force_login(self.student)
        return self.client.post(reverse('homework:toggle_task', args=[progress.id]))

    def test_an_exam_question_cannot_be_ticked_without_attempting_it(self):
        progress = self.progress_for(HomeworkTask.objects.create(
            assignment=self.assignment, task_type='exam_question', exam_question=self.question))

        self.assertEqual(self.toggle(progress).status_code, 403)
        progress.refresh_from_db()
        self.assertFalse(progress.is_completed)

    def test_a_written_exercise_is_still_ticked_by_hand(self):
        progress = self.progress_for(HomeworkTask.objects.create(
            assignment=self.assignment, task_type='custom', instructions='Ex 3.2 Q1-5'))

        self.assertEqual(self.toggle(progress).json()['status'], 'complete')
        progress.refresh_from_db()
        self.assertTrue(progress.is_completed)

    def test_the_page_shows_a_tick_box_only_for_the_written_exercise(self):
        self.progress_for(HomeworkTask.objects.create(
            assignment=self.assignment, task_type='exam_question', exam_question=self.question))
        written = self.progress_for(HomeworkTask.objects.create(
            assignment=self.assignment, task_type='custom', instructions='Ex 3.2 Q1-5'))

        self.assignment.assigned_students.add(self.student)
        self.client.force_login(self.student)
        page = self.client.get(
            reverse('homework:assignment_detail', args=[self.assignment.id])).content.decode()

        self.assertEqual(page.count('class="task-checkbox'), 1)
        self.assertIn(f'data-progress-id="{written.id}"', page)
