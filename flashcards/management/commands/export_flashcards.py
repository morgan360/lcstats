# flashcards/management/commands/export_flashcards.py
"""
Django management command to export flashcards to JSON format.

Usage:
    python manage.py export_flashcards output.json
    python manage.py export_flashcards output.json --topic coordinate-geometry
    python manage.py export_flashcards output.json --set 3
    python manage.py export_flashcards output.json --include-images
"""

from django.core.management.base import BaseCommand, CommandError
from flashcards.models import FlashcardSet, Flashcard
from interactive_lessons.models import Topic
import json
import base64
import os


class Command(BaseCommand):
    help = 'Export flashcards to JSON file'

    def add_arguments(self, parser):
        parser.add_argument(
            'output',
            type=str,
            help='Output JSON file path'
        )
        parser.add_argument(
            '--topic',
            type=str,
            help='Export only flashcards from this topic (slug)'
        )
        parser.add_argument(
            '--set',
            type=int,
            help='Export only flashcards from this set (ID)'
        )
        parser.add_argument(
            '--include-images',
            action='store_true',
            help='Include images as base64 encoded data'
        )
        parser.add_argument(
            '--pretty',
            action='store_true',
            help='Pretty-print JSON output'
        )

    def handle(self, *args, **options):
        output_path = options['output']
        topic_slug = options.get('topic')
        set_id = options.get('set')
        include_images = options['include_images']
        pretty = options['pretty']

        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('Flashcard Export Tool'))
        self.stdout.write(self.style.SUCCESS('=' * 70))

        # Build query
        flashcard_sets = FlashcardSet.objects.all().select_related('topic')

        if topic_slug:
            try:
                topic = Topic.objects.get(slug=topic_slug)
                flashcard_sets = flashcard_sets.filter(topic=topic)
                self.stdout.write(f'Filtering by topic: {topic.name}')
            except Topic.DoesNotExist:
                raise CommandError(f'Topic with slug "{topic_slug}" does not exist')

        if set_id:
            flashcard_sets = flashcard_sets.filter(id=set_id)
            self.stdout.write(f'Filtering by set ID: {set_id}')

        if not flashcard_sets.exists():
            raise CommandError('No flashcard sets found matching criteria')

        # Build export data
        export_data = {
            'version': '1.0',
            'export_metadata': {
                'include_images': include_images,
            },
            'sets': []
        }

        total_cards = 0

        for flashcard_set in flashcard_sets:
            self.stdout.write(f'\nProcessing set: {flashcard_set.topic.name} - {flashcard_set.title}')

            set_data = {
                'topic': {
                    'name': flashcard_set.topic.name,
                    'slug': flashcard_set.topic.slug,
                },
                'set': {
                    'title': flashcard_set.title,
                    'description': flashcard_set.description,
                    'order': flashcard_set.order,
                    'is_published': flashcard_set.is_published,
                },
                'cards': []
            }

            cards = flashcard_set.cards.all().order_by('order')

            for card in cards:
                card_data = {
                    'order': card.order,
                    'front_text': card.front_text,
                    'back_text': card.back_text,
                    'distractor_1': card.distractor_1,
                    'distractor_2': card.distractor_2,
                    'distractor_3': card.distractor_3,
                    'explanation': card.explanation,
                }

                # Handle images
                if include_images:
                    if card.front_image:
                        card_data['front_image'] = self._encode_image(card.front_image.path)
                        card_data['front_image_name'] = os.path.basename(card.front_image.name)

                    if card.back_image:
                        card_data['back_image'] = self._encode_image(card.back_image.path)
                        card_data['back_image_name'] = os.path.basename(card.back_image.name)
                else:
                    # Just store paths for reference
                    if card.front_image:
                        card_data['front_image_path'] = card.front_image.name
                    if card.back_image:
                        card_data['back_image_path'] = card.back_image.name

                set_data['cards'].append(card_data)
                total_cards += 1

            export_data['sets'].append(set_data)
            self.stdout.write(f'  ✓ Exported {len(set_data["cards"])} cards')

        # Write to file
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                if pretty:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
                else:
                    json.dump(export_data, f, ensure_ascii=False)

            self.stdout.write(f'\n{"=" * 70}')
            self.stdout.write(self.style.SUCCESS(f'✓ Export Complete!'))
            self.stdout.write(f'{"=" * 70}')
            self.stdout.write(f'Sets exported: {len(export_data["sets"])}')
            self.stdout.write(f'Total cards: {total_cards}')
            self.stdout.write(f'Output file: {output_path}')

            # Show file size
            file_size = os.path.getsize(output_path)
            if file_size < 1024:
                size_str = f'{file_size} bytes'
            elif file_size < 1024 * 1024:
                size_str = f'{file_size / 1024:.1f} KB'
            else:
                size_str = f'{file_size / (1024 * 1024):.1f} MB'
            self.stdout.write(f'File size: {size_str}')
            self.stdout.write(f'{"=" * 70}\n')

        except Exception as e:
            raise CommandError(f'Error writing output file: {str(e)}')

    def _encode_image(self, image_path):
        """Encode image file as base64 string"""
        try:
            with open(image_path, 'rb') as f:
                return base64.b64encode(f.read()).decode('utf-8')
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'Warning: Could not encode image {image_path}: {str(e)}')
            )
            return None
