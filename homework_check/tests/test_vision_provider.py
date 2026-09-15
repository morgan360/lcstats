"""Homework Check on its own model and provider, and full question labels.

Switched to Gemini 3.8 Flash on 2026-09-15 through Gemini's OpenAI-compatible
endpoint, with the rest of the site's vision calls left on OpenAI. These pin
what that switch depends on: the right model and client reach the call, the
OpenAI-only cache hint is not sent elsewhere, and thinking that Gemini reports
only in total_tokens still counts on the bill.
"""
from unittest import mock

from django.test import SimpleTestCase, override_settings

from exam_papers.services import vision_grading
from homework_check.services import check_analysis
from homework_check.services.assembly import merge_questions
from homework_check.services.check_analysis import (
    _usage, analyse_chunk, build_prompt, tidy_label,
)

GEMINI = dict(
    HOMEWORK_CHECK_VISION_MODEL='gemini-3.8-flash',
    HOMEWORK_CHECK_VISION_BASE_URL='https://generativelanguage.googleapis.com/v1beta/openai/',
    HOMEWORK_CHECK_VISION_API_KEY='test-key',
)


def fake_response():
    response = mock.Mock()
    response.choices = [mock.Mock(message=mock.Mock(content='{"questions": []}'))]
    response.usage = mock.Mock(prompt_tokens=100, completion_tokens=20, total_tokens=120,
                               prompt_tokens_details=None, completion_tokens_details=None)
    return response


class ProviderTests(SimpleTestCase):

    def call(self, **kw):
        with mock.patch.object(check_analysis, '_vision_completion',
                               return_value=fake_response()) as call:
            result = analyse_chunk(['p1'], ['s1'], 'Ex 1.1', cache_key='hwcheck-1', **kw)
        return call.call_args.kwargs, result

    @override_settings(**GEMINI)
    def test_gemini_gets_its_model_and_its_own_client(self):
        kwargs, result = self.call()
        self.assertEqual(kwargs['model'], 'gemini-3.8-flash')
        self.assertIn('generativelanguage.googleapis.com', str(kwargs['client'].base_url))
        self.assertEqual(result['model_used'], 'gemini-3.8-flash')

    @override_settings(**GEMINI)
    def test_the_openai_cache_hint_is_not_sent_to_gemini(self):
        kwargs, _ = self.call()
        self.assertNotIn('prompt_cache_key', kwargs)

    @override_settings(HOMEWORK_CHECK_VISION_MODEL='gpt-5.5',
                       HOMEWORK_CHECK_VISION_BASE_URL='', HOMEWORK_CHECK_VISION_API_KEY='')
    def test_blank_settings_keep_the_shared_openai_client(self):
        kwargs, _ = self.call()
        self.assertEqual(kwargs['model'], 'gpt-5.5')
        self.assertIsNone(kwargs['client'])
        self.assertEqual(kwargs['prompt_cache_key'], 'hwcheck-1')

    @override_settings(OPENAI_VISION_MODEL='gpt-5.5', **GEMINI)
    def test_the_rest_of_the_site_stays_on_openai(self):
        """Exam photo grading and work photos were never tested on Gemini."""
        self.assertEqual(vision_grading.vision_model(), 'gpt-5.5')

    def test_the_shared_helper_uses_a_client_it_is_given(self):
        client = mock.Mock()
        vision_grading._vision_completion(
            messages=[], max_tokens=10, temperature=0, model='gemini-3.8-flash', client=client)
        self.assertEqual(client.chat.completions.create.call_args.kwargs['model'],
                         'gemini-3.8-flash')


class ThinkingOnTheBillTests(SimpleTestCase):

    def usage(self, **fields):
        response = mock.Mock()
        response.usage = mock.Mock(prompt_tokens_details=None, completion_tokens_details=None,
                                   **fields)
        return _usage(response)

    def test_gemini_thinking_counts_as_output(self):
        """Measured: prompt 1108, completion 6, total 1167 -- 53 tokens of thinking."""
        u = self.usage(prompt_tokens=1108, completion_tokens=6, total_tokens=1167)
        self.assertEqual(u['completion_tokens'], 59)
        self.assertEqual(u['reasoning_tokens'], 53)

    def test_openai_totals_add_nothing(self):
        u = self.usage(prompt_tokens=100, completion_tokens=20, total_tokens=120)
        self.assertEqual(u['completion_tokens'], 20)
        self.assertEqual(u['reasoning_tokens'], 0)


class FullLabelTests(SimpleTestCase):
    """Check 27 printed Q2(i) and Q8(i) as one "(i)" row, and check 33 put
    Exercise 2.1 Q5 and 2.2 Q5 under the same "5"."""

    def test_the_prompt_asks_for_the_question_number_with_the_part(self):
        prompt = build_prompt('Exercise 2.1, 2.2', [1, 2])
        self.assertIn('"2(i)"', prompt)
        self.assertIn('never just "(i)"', prompt)
        self.assertIn('"2.1 Q5" and "2.2 Q5"', prompt)

    def test_one_spelling_per_label(self):
        self.assertEqual(tidy_label('5.'), '5')
        self.assertEqual(tidy_label(' 5 (i) '), '5(i)')
        self.assertEqual(tidy_label('Q 7'), 'Q7')
        self.assertEqual(tidy_label('2.1  Q5.'), '2.1 Q5')
        self.assertEqual(tidy_label('(iii)'), '(iii)')
        self.assertEqual(tidy_label('2.1'), '2.1')
        self.assertEqual(tidy_label('Exercise 2.1 Q5'), '2.1 Q5')
        self.assertEqual(tidy_label('Ex. 2.2 Q4'), '2.2 Q4')
        self.assertEqual(tidy_label('Extra'), 'Extra')
        self.assertEqual(tidy_label(None), '')

    def test_two_spellings_from_two_batches_merge_into_one_row(self):
        rows = check_analysis._clean_questions([
            {'label': '8.', 'verdict': 'correct', 'found_in_solutions': True},
            {'label': '8', 'verdict': 'slip', 'found_in_solutions': True},
        ])
        merged = merge_questions([{'questions': rows[:1]}, {'questions': rows[1:]}])
        self.assertEqual([r['label'] for r in merged], ['8'])

    def test_several_exercises_sort_in_book_order(self):
        rows = [{'label': l, 'verdict': 'correct', 'found_in_solutions': True,
                 'student_answer': '', 'correct_answer': '', 'comment': '',
                 'continues': False}
                for l in ('2.2 Q1', '2.1 Q10', '2.1 Q5', '2.1 Q5(b)', '2.1 Q5(a)')]
        merged = merge_questions([{'questions': rows}])
        self.assertEqual([r['label'] for r in merged],
                         ['2.1 Q5', '2.1 Q5(a)', '2.1 Q5(b)', '2.1 Q10', '2.2 Q1'])
