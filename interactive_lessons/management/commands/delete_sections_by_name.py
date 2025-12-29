"""
Management command to delete sections by name.
Run on live site to remove sections that were created there but not in local DB.
"""
from django.core.management.base import BaseCommand
from interactive_lessons.models import Section


class Command(BaseCommand):
    help = 'Delete sections by name'

    def add_arguments(self, parser):
        parser.add_argument(
            'section_names',
            nargs='+',
            type=str,
            help='Names of sections to delete',
        )

    def handle(self, *args, **options):
        section_names = options['section_names']

        for section_name in section_names:
            sections = Section.objects.filter(name=section_name)

            if not sections.exists():
                self.stdout.write(self.style.WARNING(
                    f'⚠️  No sections found with name: "{section_name}"'
                ))
                continue

            for section in sections:
                question_count = section.questions.count()

                self.stdout.write(
                    f'Found: {section.topic.name} - {section.name} '
                    f'(ID: {section.id}, {question_count} questions)'
                )

                if question_count > 0:
                    self.stdout.write(self.style.WARNING(
                        f'  ⚠️  WARNING: This section has {question_count} questions!'
                    ))
                    # Unlink questions from section (don't delete questions)
                    section.questions.update(section=None)
                    self.stdout.write('  Questions unlinked from section')

                section.delete()
                self.stdout.write(self.style.SUCCESS(f'  ✅ Deleted section: {section_name}'))

        self.stdout.write(self.style.SUCCESS('\n✅ Done!'))