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
        existing_set = FlashcardSet.objects.filter(
            title=title,
            topic__slug=topic_slug,
        ).first()

        # An existing set is updated rather than skipped, so report how the
        # cards themselves split between new and updated.
        cards = set_data.get('cards', [])
        new_cards = updated_cards = 0
        for card_data in cards:
            external_id = card_data.get('external_id')
            if external_id:
                exists = Flashcard.objects.filter(external_id=external_id).exists()
            elif existing_set is not None:
                exists = Flashcard.objects.filter(
                    flashcard_set=existing_set,
                    front_text=card_data.get('front_text', '')).exists()
            else:
                exists = False
            if exists:
                updated_cards += 1
            else:
                new_cards += 1

        previews.append({
            'title': title,
            'topic_name': topic_name,
            'topic_slug': topic_slug,
            'card_count': len(cards),
            'is_duplicate': existing_set is not None,
            'new_cards': new_cards,
            'updated_cards': updated_cards,
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
        'cards_updated': 0,
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

                # An existing set is reused rather than skipped, so that edits
                # and added cards reach a database that already has the set.
                # is_published is deliberately only applied on creation: an
                # import must never silently re-publish a set that was hidden
                # on purpose here.
                flashcard_set = FlashcardSet.objects.filter(
                    title=title, topic=topic).first()
                if flashcard_set is None:
                    flashcard_set = FlashcardSet.objects.create(
                        topic=topic,
                        title=title,
                        description=set_info.get('description', ''),
                        order=set_info.get('order', 0),
                        is_published=set_info.get('is_published', True),
                    )
                    result['sets_created'] += 1
                else:
                    result['sets_skipped'] += 1

                # Create or update flashcards
                for card_data in set_data['cards']:
                    # external_id is the identity that survives export/import;
                    # payloads written before it existed fall back to matching
                    # on question text within the set.
                    external_id = card_data.get('external_id')
                    card = None
                    if external_id:
                        card = Flashcard.objects.filter(
                            external_id=external_id).first()
                    else:
                        card = Flashcard.objects.filter(
                            flashcard_set=flashcard_set,
                            front_text=card_data['front_text']).first()

                    updating = card is not None
                    if not updating:
                        card = Flashcard()
                        if external_id:
                            card.external_id = external_id

                    card.flashcard_set = flashcard_set
                    card.order = card_data.get('order', 0)
                    card.front_text = card_data['front_text']
                    card.back_text = card_data['back_text']
                    card.distractor_1 = card_data['distractor_1']
                    card.distractor_2 = card_data['distractor_2']
                    card.distractor_3 = card_data['distractor_3']
                    card.explanation = card_data.get('explanation', '')

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
                    if updating:
                        result['cards_updated'] += 1
                    else:
                        result['cards_created'] += 1

            except Exception as e:
                title = set_data.get('set', {}).get('title', 'unknown')
                error_msg = f"Error importing set '{title}': {e}"
                result['errors'].append(error_msg)
                logger.error(error_msg)
                raise  # Rollback transaction

    return result
