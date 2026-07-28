"""
Seed starter "how do I use NumScoil" notes for NumSkull's site-help mode.

This is a management command, not a data migration, because Note.save()
calls the OpenAI embeddings API live — coupling that to `migrate` would make
deploys depend on network/API-key availability and cost tokens on every
fresh install. Run once after deploying:

    python manage.py seed_site_help_notes
"""
from django.core.management.base import BaseCommand

from notes.models import Note

STUDENT_NOTES = [
    (
        "How to mark homework as done",
        "Open **Homework** from the nav. Each task (a topic, a section, an exam "
        "question, or a QuickKick) has a checkbox or gets marked complete "
        "automatically once you finish it. Your progress bar updates as you go, "
        "and your teacher can see which tasks you've completed.",
    ),
    (
        "How flashcard mastery levels work",
        "Flashcards move through four stages: **new → learning → know → retired**. "
        "Answer correctly the first time and a card moves from new to learning; "
        "get it right again and it becomes know. Once a card is know, you're shown "
        "the answer and self-assess whether you knew it — say yes and it retires "
        "(removed from your deck); say no and it drops back to learning.",
    ),
    (
        "How solutions unlock on practice questions",
        "Full solutions are locked at first so you try the question yourself. "
        "They unlock automatically once you get the answer correct, or after a "
        "set number of attempts (usually 2) — whichever comes first. Some "
        "questions have solutions unlocked from the start.",
    ),
    (
        "What QuickKicks are",
        "QuickKicks are short videos or interactive GeoGebra applets attached to a "
        "topic, giving you a quick visual refresher. Some have a short question "
        "afterwards to check you understood it. Find them from a topic's practice "
        "page.",
    ),
    (
        "How to practice exam questions",
        "From **Interactive Lessons**, open a topic and go to its Exam Questions "
        "tab to practice real past exam questions one at a time with a suggested "
        "time limit, hints, and unlockable solutions. You can also do a full timed "
        "exam paper from the **Exam Papers** section, which uses a 150-minute "
        "countdown.",
    ),
    (
        "How your progress and score are tracked",
        "Every question you answer is recorded, right or wrong, and feeds into "
        "your overall score and topics completed on your dashboard. Using a hint "
        "reduces the score for that question by 20%, and viewing the solution "
        "reduces it by 50% — so it always pays to try first.",
    ),
]

TEACHER_NOTES = [
    (
        "How to record daily attendance and homework",
        "Open **Reports** from the nav, choose a class, and use Today's Entry. "
        "Every student defaults to Present and Homework Done — you only need to "
        "tap the students who were absent, late, or didn't do their homework. "
        "Taps save instantly; no submit button needed.",
    ),
    (
        "How to add your class timetable",
        "Timetables are managed in Django Admin under **Reports → Timetable "
        "slots**. Add one row per weekly class meeting (class, weekday, start "
        "time, optional label like a room or period). Once set, your Reports "
        "dashboard shows today's classes in order automatically.",
    ),
    (
        "How to create a class test and enter results",
        "From **Reports**, open a class and go to Tests. Create a test with a "
        "name, date, and total marks, then enter each student's score and an "
        "optional comment on one page. Leave a score blank if the student didn't "
        "sit the test.",
    ),
    (
        "How to view and export a student report",
        "From a class's **Overview** page in Reports, tap a student's name. "
        "You'll see attendance %, homework rate, test results, behaviour "
        "comments, and their NumScoil activity over any date range you choose — "
        "with buttons to download it as CSV or PDF.",
    ),
    (
        "How to assign homework to a class",
        "From the **Teacher dashboard**, create a Homework Assignment, add "
        "tasks (topics, sections, exam questions, or QuickKicks), and assign it "
        "to a whole class in one action. Students see it on their dashboard with "
        "a due date and progress tracker.",
    ),
]


class Command(BaseCommand):
    help = "Seed starter site-help notes for NumSkull's general help mode."

    def handle(self, *args, **kwargs):
        created_count = 0
        skipped_count = 0

        for audience, notes in (("student", STUDENT_NOTES), ("teacher", TEACHER_NOTES)):
            for title, content in notes:
                if Note.objects.filter(title=title).exists():
                    self.stdout.write(f"Skipping (already exists): {title}")
                    skipped_count += 1
                    continue

                Note.objects.create(
                    title=title,
                    content=content,
                    content_type="site_help",
                    audience=audience,
                )
                self.stdout.write(self.style.SUCCESS(f"Created [{audience}]: {title}"))
                created_count += 1

        self.stdout.write(
            self.style.SUCCESS(f"\nDone. Created {created_count}, skipped {skipped_count}.")
        )
