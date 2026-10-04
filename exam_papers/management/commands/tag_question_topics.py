"""Give a question the topics its parts say it is about.

``ExamQuestion.topic`` is the question's main topic: the one carrying most of
its marks. The runner-up becomes its secondary topic and the third its
need-to-know topic. The secondary is ticked to list the question only when it
carries at least a third of the marks; a superuser reviews the rest on the
worksheet page. That is a fact its parts already hold once they are tagged, so
there is no need to read the paper again -- unlike ``suggest_question_topics``,
which asks a model to judge an untagged question from its text and is the tool
for a question whose parts are bare too.

It matters beyond tidiness: a question with no topic is invisible in the
homework picker and on the topic pages, however well tagged its parts are. The
deferred 2022 papers arrived that way -- twenty questions nobody could set.

Fills blank fields only, unless ``--overwrite``. Marks decide; where a part has no
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


#: Share of a question's marks its secondary topic needs before the question
#: is listed under it as well.
LIST_SECONDARY_SHARE = 1 / 3


def ranked_topics(question):
    """[(topic, marks)] by marks carried, most first, and the total marks.

    Returns ([], 0) when no part is tagged -- nothing to go on, and a guess is
    worse than a blank.
    """
    marks = defaultdict(int)
    first_seen, topics = {}, {}
    total = 0
    for order, part in enumerate(question.parts.all()):
        if part.topic_id is None:
            continue
        weight = part.max_marks or 1
        marks[part.topic_id] += weight
        total += weight
        first_seen.setdefault(part.topic_id, order)
        topics[part.topic_id] = part.topic

    ranked = sorted(marks, key=lambda t: (-marks[t], first_seen[t]))
    return [(topics[t], marks[t]) for t in ranked], total


def proposed_topics(question, keep_main=False):
    """{field: value} the parts suggest for the question's three topics.

    With keep_main, a main topic already set stays, and the others are the
    best-carrying topics after it.
    """
    ranked, total = ranked_topics(question)
    if keep_main and question.topic_id:
        main = question.topic
    else:
        main = ranked[0][0] if ranked else None
    rest = [(t, m) for t, m in ranked if main is None or t.pk != main.pk]
    rest += [(None, 0)] * 2
    (secondary, secondary_marks), (need, _) = rest[:2]
    return {
        'topic': main,
        'secondary_topic': secondary,
        'list_under_secondary': bool(
            secondary and secondary_marks >= total * LIST_SECONDARY_SHARE),
        'need_to_know_topic': need,
    }


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
                     .select_related('exam_paper', 'topic', 'secondary_topic',
                                     'need_to_know_topic')
                     .prefetch_related('parts__topic')
                     .order_by('exam_paper__year', 'exam_paper__paper_type',
                               'question_number'))
        if options.get('paper'):
            if not ExamPaper.objects.filter(id=options['paper']).exists():
                raise CommandError(f"No paper with id {options['paper']}")
            questions = questions.filter(exam_paper_id=options['paper'])

        if options['dry_run']:
            self.stdout.write(self.style.WARNING(
                "Dry run: nothing will be written."))

        changed, unchanged, bare = 0, 0, []
        for question in questions:
            proposal = proposed_topics(question, keep_main=not options['overwrite'])
            if not any(p.topic_id for p in question.parts.all()):
                if question.topic_id is None:
                    bare.append(question)
                continue

            updates = {}
            for field in ('topic', 'secondary_topic', 'need_to_know_topic'):
                current = getattr(question, field)
                wanted = proposal[field]
                if current == wanted or (current and not options['overwrite']):
                    continue
                updates[field] = wanted
            if 'secondary_topic' in updates:
                updates['list_under_secondary'] = proposal['list_under_secondary']
            # Never leave a topic in two slots after a partial fill.
            final = {f: updates.get(f, getattr(question, f))
                     for f in ('topic', 'secondary_topic', 'need_to_know_topic')}
            ids = [t.pk for t in final.values() if t]
            if len(ids) != len(set(ids)):
                updates = {}

            if not updates:
                unchanged += 1
                continue

            described = ", ".join(
                f"{f.replace('_', ' ')} -> {v.name if hasattr(v, 'name') else v}"
                for f, v in updates.items())
            self.stdout.write(
                f"  {question.exam_paper} Q{question.question_number}: {described}")
            if not options['dry_run']:
                for field, value in updates.items():
                    setattr(question, field, value)
                question.save(update_fields=list(updates))
            changed += 1

        for question in bare:
            self.stdout.write(self.style.WARNING(
                f"  {question.exam_paper} Q{question.question_number}: no part "
                f"is tagged -- tag the parts, or try suggest_question_topics"))

        self.stdout.write(self.style.SUCCESS(
            f"{changed} question(s) tagged, {unchanged} already right, "
            f"{len(bare)} with nothing to go on."))
