"""
Django management command to import flashcards from JSON export.

Usage:
    python manage.py import_flashcards /path/to/flashcards_export.json
"""

import json
from django.core.management.base import BaseCommand
from django.db import transaction
from flashcards.models import FlashcardSet, Flashcard
from flashcards.services import import_flashcards_from_data


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

        if 'sets' not in data:
            self.stdout.write(self.style.ERROR("Invalid format: 'sets' key not found"))
            return

        if clear_existing:
            self.stdout.write(self.style.WARNING("Clearing all existing flashcards..."))
            with transaction.atomic():
                Flashcard.objects.all().delete()
                FlashcardSet.objects.all().delete()
            self.stdout.write(self.style.SUCCESS("Cleared all flashcards"))

        result = import_flashcards_from_data(data)

        # Summary
        self.stdout.write(self.style.SUCCESS(f"\nImport complete!"))
        self.stdout.write(f"  Flashcard sets created: {result['sets_created']}")
        self.stdout.write(f"  Flashcards created: {result['cards_created']}")
        self.stdout.write(f"  Sets skipped (duplicates): {result['sets_skipped']}")

        if result['errors']:
            self.stdout.write(self.style.WARNING(f"\n{len(result['errors'])} errors occurred:"))
            for error in result['errors']:
                self.stdout.write(f"  - {error}")
