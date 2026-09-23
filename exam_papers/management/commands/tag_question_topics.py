"""Give a question the topic its parts say it is about.

``ExamQuestion.topic`` is the question's dominant topic: the one carrying most
of its marks. That is a fact its parts already hold once they are tagged, so
there is no need to read the paper again -- unlike ``suggest_question_topics``,
which asks a model to judge an untagged question from its text and is the tool
for a question whose parts are bare too.

It matters beyond tidiness: a question with no topic is invisible in the
homework picker and on the topic pages, however well tagged its parts are. The
deferred 2022 papers arrived that way -- twenty questions nobody could set.

Fills blanks only, unless ``--overwrite``. Marks decide; where a part has no
``max_marks`` it counts as one mark, so a tagged part is never worth nothing.
A tie goes to the topic that appears earliest in the question, because that is
the one a teacher naming the question would say first.

    python manage.py tag_question_topics --dry-run
    python manage.py tag_question_topics --paper 31
    python manage.py tag_question_topics --overwrite
"""
from collections import defaultdict

from django.core.management.base import BaseCommand, CommandError

from exam_papers.models import ExamPaper, ExamQuestion


def dominant_topic(question):
    """(topic, marks, total) for the topic carrying most of a question's marks.

    Returns (None, 0, 0) when no part is tagged -- nothing to go on, and a
    guess is worse than a blank.
    """
    marks = defaultdict(int)
    first_seen = {}
    total = 0
    for order, part in enumerate(question.parts.all()):
        if part.topic_id is None:
            continue
        weight = part.max_marks or 1
        marks[part.topic_id] += weight
        total += weight
        first_seen.setdefault(part.topic_id, order)

    if not marks:
        return None, 0, 0

    topic_id = max(marks, key=lambda t: (marks[t], -first_seen[t]))
    topic = next(p.topic for p in question.parts.all() if p.topic_id == topic_id)
    return topic, marks[topic_id], total


class Command(BaseCommand):
    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument('--paper', type=int, help='Only this paper id')
        parser.add_argument('--dry-run', action='store_true',
                            help='Report what would change, writing nothing')
        parser.add_argument('--overwrite', action='store_true',
                            help='Also replace topics already set')

    def handle(self, *args, **options):
        questions = (ExamQuestion.objects
                     .select_related('exam_paper', 'topic')
                     .prefetch_related('parts__topic')
                     .order_by('exam_paper__year', 'exam_paper__paper_type',
                               'question_number'))
        if options.get('paper'):
            if not ExamPaper.objects.filter(id=options['paper']).exists():
                raise CommandError(f"No paper with id {options['paper']}")
            questions = questions.filter(exam_paper_id=options['paper'])
        if not options['overwrite']:
            questions = questions.filter(topic__isnull=True)

        if options['dry_run']:
            self.stdout.write(self.style.WARNING(
                "Dry run: nothing will be written."))

        changed, unchanged, bare = 0, 0, []
        for question in questions:
            topic, marks, total = dominant_topic(question)
            if topic is None:
                bare.append(question)
                continue
            if question.topic_id == topic.id:
                unchanged += 1
                continue

            was = question.topic.name if question.topic else "nothing"
            self.stdout.write(
                f"  {question.exam_paper} Q{question.question_number}: "
                f"{was} -> {topic.name} ({marks} of {total} marks)")
            if not options['dry_run']:
                question.topic = topic
                question.save(update_fields=['topic'])
            changed += 1

        for question in bare:
            self.stdout.write(self.style.WARNING(
                f"  {question.exam_paper} Q{question.question_number}: no part "
                f"is tagged -- tag the parts, or try suggest_question_topics"))

        self.stdout.write(self.style.SUCCESS(
            f"{changed} question(s) tagged, {unchanged} already right, "
            f"{len(bare)} with nothing to go on."))
