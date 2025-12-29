"""
Management command to fix duplicate sections with same slug.
This merges duplicate sections and reassigns questions to the correct one.
"""
from django.core.management.base import BaseCommand
from django.db.models import Count
from interactive_lessons.models import Section, Question


class Command(BaseCommand):
    help = 'Fix duplicate sections with the same slug'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Checking for duplicate section slugs...'))

        # Find all duplicate slugs
        duplicates = (
            Section.objects.values('slug')
            .annotate(count=Count('id'))
            .filter(count__gt=1)
        )

        if not duplicates:
            self.stdout.write(self.style.SUCCESS('✅ No duplicate sections found!'))
            return

        for dup in duplicates:
            slug = dup['slug']
            sections = Section.objects.filter(slug=slug).order_by('id')

            self.stdout.write(f"\n⚠️  Found {sections.count()} sections with slug: {slug}")

            for section in sections:
                question_count = section.questions.count()
                self.stdout.write(
                    f"  - Section {section.id}: {section.topic.name} - {section.name} "
                    f"({question_count} questions)"
                )

            # Ask user which section to keep
            self.stdout.write(self.style.WARNING(
                f"\nWhich section should we keep? (Enter section ID)"
            ))

            # For automated fix, keep the first one (lowest ID)
            keep_section = sections.first()

            self.stdout.write(f"Keeping Section {keep_section.id}: {keep_section.topic.name} - {keep_section.name}")

            # Move all questions from other sections to the keeper
            for section in sections:
                if section.id != keep_section.id:
                    questions = section.questions.all()
                    question_count = questions.count()

                    if question_count > 0:
                        self.stdout.write(
                            f"  Moving {question_count} questions from Section {section.id} to {keep_section.id}"
                        )
                        questions.update(section=keep_section)

                    # Delete the duplicate section
                    self.stdout.write(f"  Deleting duplicate Section {section.id}")
                    section.delete()

            self.stdout.write(self.style.SUCCESS(
                f"✅ Fixed duplicate sections for slug: {slug}"
            ))

        self.stdout.write(self.style.SUCCESS('\n✅ All duplicate sections fixed!'))