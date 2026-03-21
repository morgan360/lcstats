"""
Reusable service functions for flashcard import/export.
Used by both the management command and the web import view.
"""

import base64
import logging

from django.core.files.base import ContentFile
from django.db import transaction

from flashcards.models import FlashcardSet, Flashcard
from interactive_lessons.models import Topic

logger = logging.getLogger(__name__)


def preview_flashcard_import(data: dict) -> list[dict]:
    """
    Preview what would be imported without writing to the database.

    Returns list of dicts with:
        title, topic_name, topic_slug, card_count, is_duplicate, topic_exists
    """
    if 'sets' not in data:
        return []

    previews = []
    for set_data in data['sets']:
        topic_data = set_data.get('topic', {})
        set_info = set_data.get('set', {})
        title = set_info.get('title', 'Untitled')
        topic_slug = topic_data.get('slug', '')
        topic_name = topic_data.get('name', 'Unknown')

        topic_exists = Topic.objects.filter(slug=topic_slug).exists()
        is_duplicate = FlashcardSet.objects.filter(
            title=title,
            topic__slug=topic_slug,
        ).exists()

        previews.append({
            'title': title,
            'topic_name': topic_name,
            'topic_slug': topic_slug,
            'card_count': len(set_data.get('cards', [])),
            'is_duplicate': is_duplicate,
            'topic_exists': topic_exists,
        })

    return previews


def import_flashcards_from_data(data: dict) -> dict:
    """
    Import flashcards from parsed JSON data.

    Args:
        data: Parsed JSON with 'sets' key containing flashcard set data.

    Returns:
        dict with keys: sets_created, cards_created, sets_skipped, errors
    """
    result = {
        'sets_created': 0,
        'cards_created': 0,
        'sets_skipped': 0,
        'errors': [],
    }

    if 'sets' not in data:
        result['errors'].append("Invalid format: 'sets' key not found")
        return result

    with transaction.atomic():
        for set_data in data['sets']:
            try:
                topic_data = set_data['topic']
                set_info = set_data['set']
                title = set_info.get('title', 'Untitled')

                # Get or create topic
                topic, _ = Topic.objects.get_or_create(
                    slug=topic_data['slug'],
                    defaults={'name': topic_data['name']},
                )

                # Duplicate detection
                if FlashcardSet.objects.filter(title=title, topic=topic).exists():
                    result['sets_skipped'] += 1
                    continue

                # Create flashcard set
                flashcard_set = FlashcardSet.objects.create(
                    topic=topic,
                    title=title,
                    description=set_info.get('description', ''),
                    order=set_info.get('order', 0),
                    is_published=set_info.get('is_published', True),
                )
                result['sets_created'] += 1

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
                        explanation=card_data.get('explanation', ''),
                    )

                    # Handle front image
                    if card_data.get('front_image'):
                        try:
                            image_data = base64.b64decode(card_data['front_image'])
                            card.front_image = ContentFile(
                                image_data, name=f'front_{card.order}.png'
                            )
                        except Exception as e:
                            logger.warning("Failed to decode front image: %s", e)

                    # Handle back image
                    if card_data.get('back_image'):
                        try:
                            image_data = base64.b64decode(card_data['back_image'])
                            card.back_image = ContentFile(
                                image_data, name=f'back_{card.order}.png'
                            )
                        except Exception as e:
                            logger.warning("Failed to decode back image: %s", e)

                    card.save()
                    result['cards_created'] += 1

            except Exception as e:
                title = set_data.get('set', {}).get('title', 'unknown')
                error_msg = f"Error importing set '{title}': {e}"
                result['errors'].append(error_msg)
                logger.error(error_msg)
                raise  # Rollback transaction

    return result
