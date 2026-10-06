"""Homework help: the shape of the request, and the rule it exists to keep.

Two things here would never show up in a happy-path test. The order of the
request is a cost decision (see test_request_shape.py): the solution pages
have to come before anything that varies, or every student asking about the
same exercise pays for them in full. And the student may not have the
solutions, so the prompt has to forbid handing over the answer -- the reverse
of Homework Check's own prompt, which states answers for a teacher.
"""
from unittest import mock

from django.test import TestCase, override_settings

from homework_check.services import question_help

from .test_request_shape import fake_response, kinds, sent_content


class FakeSection:
    pk = 7
    label = "Exercise 2.3"
    page_range = "17-18"
    solution = None


class QuestionHelpRequestTests(TestCase):

    def analyse(self, label="5(ii)"):
        with mock.patch.object(question_help, "encode_section_pages",
                               return_value=(["s1", "s2"], [17, 18])), \
                mock.patch.object(question_help, "_vision_completion",
                                  return_value=fake_response('{"readable": true}')) as call:
            result = question_help.analyse_question("photo", FakeSection(), label)
        return sent_content(call.call_args), call.call_args, result

    def test_prompt_then_solution_pages_then_the_question_and_photo(self):
        content, _, _ = self.analyse()
        urls = [part["image_url"]["url"] for part in content
                if part["type"] == "image_url"]

        self.assertEqual(content[0]["type"], "text", kinds(content))
        self.assertEqual(len(urls), 3)
        self.assertTrue(urls[0].endswith("s1") and urls[1].endswith("s2"),
                        f"solution pages should come first, got {kinds(content)}")
        self.assertTrue(urls[2].endswith("photo"),
                        f"the photo should come last, got {kinds(content)}")

    def test_the_question_number_stays_out_of_the_cached_prefix(self):
        content, _, _ = self.analyse(label="5(ii)")
        last_page = max(i for i, part in enumerate(content)
                        if part["type"] == "image_url" and part["image_url"]["url"].endswith("s2"))
        prefix = " ".join(part.get("text", "") for part in content[:last_page + 1])
        self.assertNotIn("5(ii)", prefix)
        self.assertIn("5(ii)", " ".join(part.get("text", "") for part in content[last_page:]))

    def test_the_prompt_forbids_giving_the_answer_away(self):
        prompt = question_help.build_prompt("Exercise 2.3")
        self.assertIn("Never give the answer away", prompt)
        self.assertIn("The student cannot see them", prompt)
        self.assertIn("do NOT quote, copy or paraphrase any step of the worked solutions", prompt)

    def test_usage_is_recorded_for_the_spend_page(self):
        from homework_check.models import VisionUsage

        self.analyse()
        row = VisionUsage.objects.get()
        self.assertIsNone(row.hw_check)
        self.assertEqual(row.prompt_tokens, 100)

    @override_settings(HOMEWORK_CHECK_MAX_SOLUTION_PAGES=2)
    def test_an_exercise_over_the_cap_is_unavailable_with_a_safe_message(self):
        with mock.patch.object(question_help, "pages_for_check",
                               return_value=[mock.Mock()] * 3):
            with self.assertRaises(question_help.Unavailable) as raised:
                question_help.encode_section_pages(FakeSection())
        self.assertEqual(str(raised.exception),
                         "Help isn't available for this exercise yet.")
