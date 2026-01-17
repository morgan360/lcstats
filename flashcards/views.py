from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from interactive_lessons.models import Topic
from .models import FlashcardSet, Flashcard, FlashcardAttempt
import json
import markdown
from markdown_katex import KatexExtension


@login_required
def flashcard_sets_index(request):
    """
    Display all published flashcard sets across all topics.
    Following quickkicks_index pattern.
    """
    sets = FlashcardSet.objects.filter(
        is_published=True
    ).select_related('topic').order_by('topic__name', 'order', 'title')

    context = {
        'flashcard_sets': sets,
    }
    return render(request, 'flashcards/index.html', context)


@login_required
def flashcard_sets_list(request, topic_slug):
    """
    Display all flashcard sets for a specific topic.
    Shows progress summary for each set.
    """
    topic = get_object_or_404(Topic, slug=topic_slug)
    sets = FlashcardSet.objects.filter(
        topic=topic,
        is_published=True
    ).prefetch_related('cards').order_by('order', 'title')

    # Annotate with student's progress
    sets_with_progress = []
    for flashcard_set in sets:
        # Get all cards in set
        card_ids = flashcard_set.cards.values_list('id', flat=True)

        # Get student's attempts for these cards
        attempts = FlashcardAttempt.objects.filter(
            student=request.user,
            flashcard_id__in=card_ids
        )

        # Calculate mastery breakdown
        mastery_counts = {
            'new': card_ids.count() - attempts.count(),  # Cards never seen
            'learning': attempts.filter(mastery_level='learning').count(),
            'know': attempts.filter(mastery_level='know').count(),
            'dont_know': attempts.filter(mastery_level='dont_know').count(),
            'retired': attempts.filter(mastery_level='retired').count(),
        }

        # Progress is based on know + retired cards
        mastered = mastery_counts['know'] + mastery_counts['retired']
        sets_with_progress.append({
            'set': flashcard_set,
            'total_cards': card_ids.count(),
            'mastery_counts': mastery_counts,
            'progress_pct': (mastered / card_ids.count() * 100) if card_ids.count() > 0 else 0
        })

    context = {
        'topic': topic,
        'sets_with_progress': sets_with_progress,
    }
    return render(request, 'flashcards/sets_list.html', context)


@login_required
def study_set(request, topic_slug, set_id):
    """
    Main study interface - shows cards one by one.
    - Cards in 'new', 'learning', 'dont_know' states: Multiple choice
    - Cards in 'know' state: Self-assessment mode
    - Cards in 'retired' state: Filtered out of deck
    Uses AJAX for answer submission to avoid page refresh.
    """
    topic = get_object_or_404(Topic, slug=topic_slug)
    flashcard_set = get_object_or_404(FlashcardSet, id=set_id, topic=topic, is_published=True)

    # Get all cards in order
    all_cards = flashcard_set.cards.all().order_by('order')

    if not all_cards.exists():
        return render(request, 'flashcards/no_cards.html', {'flashcard_set': flashcard_set, 'topic': topic})

    # Get or create attempts for all cards (initialize on first view)
    attempts_map = {}
    for card in all_cards:
        attempt, created = FlashcardAttempt.objects.get_or_create(
            student=request.user,
            flashcard=card
        )
        attempts_map[card.id] = attempt

    # Filter out retired cards for study session
    cards = [card for card in all_cards if attempts_map[card.id].mastery_level != 'retired']

    # Check if all cards are retired
    if not cards:
        retired_count = all_cards.count()
        return render(request, 'flashcards/all_retired.html', {
            'flashcard_set': flashcard_set,
            'topic': topic,
            'retired_count': retired_count,
        })

    # Record view for non-retired cards
    for card in cards:
        attempts_map[card.id].record_view()

    # Prepare card data for frontend (with shuffled options)
    cards_data = []

    for card in cards:
        # Create fresh markdown instance for each conversion to avoid state issues
        md_front = markdown.Markdown(extensions=[KatexExtension()])
        md_back = markdown.Markdown(extensions=[KatexExtension()])
        md_exp = markdown.Markdown(extensions=[KatexExtension()])

        attempt = attempts_map[card.id]
        is_self_assess = attempt.mastery_level == 'know'

        # Render options with markdown (only needed for multiple choice mode)
        shuffled_options = card.get_shuffled_options()
        for option in shuffled_options:
            md_opt = markdown.Markdown(extensions=[KatexExtension()])
            option['text'] = md_opt.convert(option['text'])

        cards_data.append({
            'id': card.id,
            'front_text': md_front.convert(card.front_text),
            'front_image': card.front_image.url if card.front_image else None,
            'back_text': md_back.convert(card.back_text),
            'back_image': card.back_image.url if card.back_image else None,
            'explanation': md_exp.convert(card.explanation) if card.explanation else None,
            'options': shuffled_options,  # Already shuffled with rendered text
            'order': card.order,
            'is_self_assess': is_self_assess,  # True for 'know' cards
            'attempt': {
                'mastery_level': attempt.mastery_level,
                'view_count': attempt.view_count,
                'correct_count': attempt.correct_count,
                'incorrect_count': attempt.incorrect_count,
            }
        })

    context = {
        'topic': topic,
        'flashcard_set': flashcard_set,
        'cards_data': json.dumps(cards_data),  # Pass to frontend as JSON
        'total_cards': len(cards),
        'total_in_set': all_cards.count(),
        'retired_count': all_cards.count() - len(cards),
    }
    return render(request, 'flashcards/study.html', context)


@login_required
@require_POST
def record_answer(request):
    """
    AJAX endpoint to record student's answer.
    Handles both multiple choice and self-assessment modes.
    Returns updated mastery state and statistics.
    """
    try:
        data = json.loads(request.body)
        card_id = data.get('card_id')
        selected_option_id = data.get('selected_option_id')
        is_self_assessed = data.get('is_self_assessed', False)

        # Get card
        card = get_object_or_404(Flashcard, id=card_id)

        # Determine if answer is correct
        if is_self_assessed:
            # Self-assessment mode: is_correct comes directly from frontend
            is_correct = data.get('is_correct', False)
        else:
            # Multiple choice mode: check if selected option is correct
            is_correct = (selected_option_id == 'correct')

        # Get or create attempt
        attempt, created = FlashcardAttempt.objects.get_or_create(
            student=request.user,
            flashcard=card
        )

        # Record the answer (updates mastery automatically)
        attempt.record_answer(is_correct, is_self_assessed=is_self_assessed)

        # Return updated state
        return JsonResponse({
            'success': True,
            'is_correct': is_correct,
            'new_mastery_level': attempt.mastery_level,
            'mastery_display': attempt.get_mastery_level_display(),
            'correct_count': attempt.correct_count,
            'incorrect_count': attempt.incorrect_count,
            'view_count': attempt.view_count,
            'is_retired': attempt.mastery_level == 'retired',
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required
def set_progress(request, topic_slug, set_id):
    """
    Show detailed progress for a flashcard set.
    Lists all cards with mastery status including retired.
    """
    topic = get_object_or_404(Topic, slug=topic_slug)
    flashcard_set = get_object_or_404(FlashcardSet, id=set_id, topic=topic, is_published=True)

    cards = flashcard_set.cards.all().order_by('order')

    # Get attempts
    attempts = FlashcardAttempt.objects.filter(
        student=request.user,
        flashcard__in=cards
    ).select_related('flashcard')

    attempts_map = {attempt.flashcard_id: attempt for attempt in attempts}

    # Build progress data
    cards_progress = []
    for card in cards:
        attempt = attempts_map.get(card.id)
        accuracy = None
        if attempt and (attempt.correct_count + attempt.incorrect_count) > 0:
            accuracy = (attempt.correct_count / (attempt.correct_count + attempt.incorrect_count) * 100)

        cards_progress.append({
            'card': card,
            'attempt': attempt,
            'mastery': attempt.get_mastery_level_display() if attempt else 'New',
            'mastery_level': attempt.mastery_level if attempt else 'new',
            'accuracy': accuracy
        })

    # Overall statistics
    total_cards = cards.count()
    know_count = len([cp for cp in cards_progress if cp['attempt'] and cp['attempt'].mastery_level == 'know'])
    retired_count = len([cp for cp in cards_progress if cp['attempt'] and cp['attempt'].mastery_level == 'retired'])
    mastered = know_count + retired_count

    context = {
        'topic': topic,
        'flashcard_set': flashcard_set,
        'cards_progress': cards_progress,
        'total_cards': total_cards,
        'mastered_count': mastered,
        'know_count': know_count,
        'retired_count': retired_count,
        'progress_pct': (mastered / total_cards * 100) if total_cards > 0 else 0,
    }
    return render(request, 'flashcards/progress.html', context)


@login_required
@require_POST
def demote_card(request):
    """
    AJAX endpoint to demote a 'know' card back to 'learning' state.
    Used when student wants to go back to multiple choice mode.
    """
    try:
        data = json.loads(request.body)
        card_id = data.get('card_id')

        # Get card and attempt
        card = get_object_or_404(Flashcard, id=card_id)
        attempt = get_object_or_404(FlashcardAttempt, student=request.user, flashcard=card)

        # Demote to learning
        success = attempt.demote_to_learning()

        if success:
            return JsonResponse({
                'success': True,
                'new_mastery_level': attempt.mastery_level,
                'mastery_display': attempt.get_mastery_level_display(),
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Card is not in "know" state'
            }, status=400)

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required
@require_POST
def reset_card_progress(request):
    """
    AJAX endpoint to reset a single card's progress.
    """
    try:
        data = json.loads(request.body)
        card_id = data.get('card_id')

        # Get card and attempt
        card = get_object_or_404(Flashcard, id=card_id)
        attempt = get_object_or_404(FlashcardAttempt, student=request.user, flashcard=card)

        # Reset progress
        attempt.reset_progress()

        return JsonResponse({
            'success': True,
            'new_mastery_level': attempt.mastery_level,
            'mastery_display': attempt.get_mastery_level_display(),
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required
@require_POST
def reset_set_progress(request, topic_slug, set_id):
    """
    Reset all progress for a flashcard set.
    Redirects back to study page.
    """
    from django.contrib import messages

    topic = get_object_or_404(Topic, slug=topic_slug)
    flashcard_set = get_object_or_404(FlashcardSet, id=set_id, topic=topic, is_published=True)

    # Reset all attempts for this set
    FlashcardAttempt.reset_set_progress(request.user, flashcard_set)

    messages.success(request, f'Progress for "{flashcard_set.title}" has been reset.')

    # Check if AJAX request
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True})

    # Redirect to study page
    from django.shortcuts import redirect
    from django.urls import reverse
    return redirect(reverse('flashcards:study_set', kwargs={
        'topic_slug': topic_slug,
        'set_id': set_id
    }))
