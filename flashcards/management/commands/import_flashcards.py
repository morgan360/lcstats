"""
Django management command to import flashcards from JSON export.

Usage:
    python manage.py import_flashcards /path/to/flashcards_export.json
"""

import json
import base64
from io import BytesIO
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from django.db import transaction
from flashcards.models import FlashcardSet, Flashcard
from interactive_lessons.models import Topic


class Command(BaseCommand):
    help = 'Import flashcards from JSON export file'

    def add_arguments(self, parser):
        parser.add_argument(
            'json_file',
            type=str,
            help='Path to the JSON export file'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear all existing flashcards before importing'
        )

    def handle(self, *args, **options):
        json_file = options['json_file']
        clear_existing = options.get('clear', False)

        self.stdout.write(f"Loading flashcards from {json_file}...")

        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f"File not found: {json_file}"))
            return
        except json.JSONDecodeError as e:
            self.stdout.write(self.style.ERROR(f"Invalid JSON: {e}"))
            return

        # Validate data structure
        if 'sets' not in data:
            self.stdout.write(self.style.ERROR("Invalid format: 'sets' key not found"))
            return

        if clear_existing:
            self.stdout.write(self.style.WARNING("Clearing all existing flashcards..."))
            with transaction.atomic():
                Flashcard.objects.all().delete()
                FlashcardSet.objects.all().delete()
            self.stdout.write(self.style.SUCCESS("Cleared all flashcards"))

        # Import data
        sets_created = 0
        cards_created = 0
        errors = []

        with transaction.atomic():
            for set_data in data['sets']:
                try:
                    # Get or create topic
                    topic_data = set_data['topic']
                    topic, _ = Topic.objects.get_or_create(
                        slug=topic_data['slug'],
                        defaults={'name': topic_data['name']}
                    )

                    # Create flashcard set
                    set_info = set_data['set']
                    flashcard_set = FlashcardSet.objects.create(
                        topic=topic,
                        title=set_info['title'],
                        description=set_info.get('description', ''),
                        order=set_info.get('order', 0),
                        is_published=set_info.get('is_published', True)
                    )
                    sets_created += 1

                    # Create flashcards
                    for card_data in set_data['cards']:
                        card = Flashcard(
                            flashcard_set=flashcard_set,
                            order=card_data.get('order', 0),
                            front_text=card_data['front_text'],
                            back_text=card_data['back_text'],
                            distractor_1=card_data['distractor_1'],
                            distractor_2=card_data['distractor_2'],
                            distractor_3=card_data['distractor_3'],
                            explanation=card_data.get('explanation', '')
                        )

                        # Handle front image if present
                        if 'front_image' in card_data and card_data['front_image']:
                            try:
                                image_data = base64.b64decode(card_data['front_image'])
                                image_file = ContentFile(image_data, name=f'front_{card.order}.png')
                                card.front_image = image_file
                            except Exception as e:
                                self.stdout.write(
                                    self.style.WARNING(f"Failed to decode front image: {e}")
                                )

                        # Handle back image if present
                        if 'back_image' in card_data and card_data['back_image']:
                            try:
                                image_data = base64.b64decode(card_data['back_image'])
                                image_file = ContentFile(image_data, name=f'back_{card.order}.png')
                                card.back_image = image_file
                            except Exception as e:
                                self.stdout.write(
                                    self.style.WARNING(f"Failed to decode back image: {e}")
                                )

                        card.save()
                        cards_created += 1

                except Exception as e:
                    error_msg = f"Error importing set '{set_info.get('title', 'unknown')}': {e}"
                    errors.append(error_msg)
                    self.stdout.write(self.style.ERROR(error_msg))
                    raise  # Rollback transaction

        # Summary
        self.stdout.write(self.style.SUCCESS(f"\nImport complete!"))
        self.stdout.write(f"  Flashcard sets created: {sets_created}")
        self.stdout.write(f"  Flashcards created: {cards_created}")

        if errors:
            self.stdout.write(self.style.WARNING(f"\n{len(errors)} errors occurred:"))
            for error in errors:
                self.stdout.write(f"  - {error}")