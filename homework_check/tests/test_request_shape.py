"""The order the request is built in, which is a cost decision.

OpenAI discounts a request only where it shares an exact prefix with a recent
one. The solution pages are identical for every batch of a check and for every
student marked against the same exercise, so they have to sit ahead of the
photographs, which are different every time. Built the other way round the
pages fall behind content that never repeats and are paid for in full on every
batch -- measured at 14,302 prompt tokens with 0 cached against 14,328 with
10,368 cached, on the same eight photographs and eleven solution pages.

None of that is visible in the report, so nothing else in this suite would
notice it being undone. Hence these tests, which assert the shape of the
request rather than anything about the answer.
"""
from unittest import mock

from django.test import TestCase, override_settings

from homework_check.services import runner
from homework_check.services.check_analysis import analyse_chunk, build_prompt


def fake_response(content='{"questions": []}'):
    response = mock.Mock()
    response.choices = [mock.Mock(message=mock.Mock(content=content))]
    response.usage = mock.Mock(
        prompt_tokens=100, completion_tokens=20,
        prompt_tokens_details=mock.Mock(cached_tokens=64),
    )
    return response


def sent_content(call):
    return call.kwargs["messages"][0]["content"]


def kinds(content):
    """The content parts as a readable sequence, e.g. ['text', 'image', ...]."""
    return [
        "image" if part["type"] == "image_url" else part["text"][:40]
        for part in content
    ]


class RequestOrderTests(TestCase):

    def analyse(self, photos=("p1", "p2"), pages=("s1", "s2", "s3"), **kw):
        with mock.patch(
            "homework_check.services.check_analysis._vision_completion",
            return_value=fake_response(),
        ) as call:
            analyse_chunk(list(photos), list(pages), "Ex 1.1", **kw)
        return sent_content(call.call_args), call.call_args

    def test_the_solution_pages_are_sent_before_the_student_photos(self):
        """The whole point: the repeated content has to come first."""
        content, _ = self.analyse(photos=["p1", "p2"], pages=["s1", "s2", "s3"])

        images = [i for i, part in enumerate(content)
                  if part["type"] == "image_url"]
        urls = [content[i]["image_url"]["url"] for i in images]

        self.assertEqual(len(urls), 5)
        self.assertTrue(all("s" in u for u in urls[:3]),
                        f"solution pages should come first, got {kinds(content)}")
        self.assertTrue(all("p" in u for u in urls[3:]),
                        f"photos should come last, got {kinds(content)}")

    def test_the_prompt_is_the_very_first_thing_in_the_request(self):
        content, _ = self.analyse()
        self.assertEqual(content[0]["type"], "text")
        self.assertIn("Leaving Certificate", content[0]["text"])

    def test_two_batches_of_one_check_share_an_identical_prefix(self):
        """Right up to the heading above the photos, which is where they differ.

        This is the property the discount is actually paid on, so it is worth
        asserting directly rather than inferring it from the ordering.
        """
        first, _ = self.analyse(photos=["a1", "a2"], pages=["s1", "s2"],
                                chunk_label="photos 1-2")
        second, _ = self.analyse(photos=["b1", "b2"], pages=["s1", "s2"],
                                 chunk_label="photos 3-4")

        # prompt + heading + 2 solution images = the shared prefix.
        self.assertEqual(first[:4], second[:4])
        self.assertNotEqual(first[4], second[4])

    def test_a_short_final_batch_still_shares_that_prefix(self):
        """A six-photo check ends on a batch of two, and must not lose the cache.

        The photo count used to be written into the prompt, which put a
        difference in the first few tokens of the request and pushed the
        solution pages out of the cache for exactly the batch that had least
        to gain from being cheap.
        """
        full, _ = self.analyse(photos=["a1", "a2", "a3", "a4"],
                               pages=["s1", "s2"], chunk_label="photos 1-4")
        rump, _ = self.analyse(photos=["b1", "b2"],
                               pages=["s1", "s2"], chunk_label="photos 5-6")
        self.assertEqual(full[:4], rump[:4])

    def test_the_prompt_says_nothing_that_changes_between_batches(self):
        prompt = build_prompt("Ex 1.1", [2, 3, 4])
        self.assertNotIn("in this batch", prompt)
        for label in ("photos 1-4", "photos 5-8"):
            self.assertNotIn(label, prompt)

    def test_the_photo_count_still_reaches_the_model(self):
        """Dropped from the prompt, so it has to be on the heading instead."""
        content, _ = self.analyse(photos=["p1", "p2", "p3"],
                                  chunk_label="photos 1-3")
        heading = [p["text"] for p in content
                   if p["type"] == "text"
                   and p["text"].startswith("**The student's work")]
        self.assertEqual(len(heading), 1)
        self.assertIn("3", heading[0])
        self.assertIn("photos 1-3", heading[0])

    def test_a_check_with_no_solution_pages_still_builds(self):
        content, _ = self.analyse(pages=[])
        self.assertNotIn("The worked solutions", " ".join(
            p["text"] for p in content if p["type"] == "text"))


class CacheKeyTests(TestCase):

    def test_the_cache_key_is_sent_when_given(self):
        with mock.patch(
            "homework_check.services.check_analysis._vision_completion",
            return_value=fake_response(),
        ) as call:
            analyse_chunk(["p"], ["s"], "Ex 1.1", cache_key="hwcheck-1-2-12")
        self.assertEqual(call.call_args.kwargs["prompt_cache_key"],
                         "hwcheck-1-2-12")

    def test_no_key_is_sent_when_there_is_none(self):
        """Rather than an empty string, which is a value the API would see."""
        with mock.patch(
            "homework_check.services.check_analysis._vision_completion",
            return_value=fake_response(),
        ) as call:
            analyse_chunk(["p"], ["s"], "Ex 1.1")
        self.assertNotIn("prompt_cache_key", call.call_args.kwargs)

    def test_cached_tokens_are_reported_back(self):
        with mock.patch(
            "homework_check.services.check_analysis._vision_completion",
            return_value=fake_response(),
        ):
            result = analyse_chunk(["p"], ["s"], "Ex 1.1")
        self.assertEqual(result["usage"]["cached_tokens"], 64)

    def test_cached_tokens_default_to_zero_when_the_api_omits_them(self):
        response = fake_response()
        response.usage = mock.Mock(prompt_tokens=1, completion_tokens=1,
                                   prompt_tokens_details=None)
        with mock.patch(
            "homework_check.services.check_analysis._vision_completion",
            return_value=response,
        ):
            result = analyse_chunk(["p"], ["s"], "Ex 1.1")
        self.assertEqual(result["usage"]["cached_tokens"], 0)


@override_settings(HOMEWORK_CHECK_MAX_SOLUTION_PAGES=30)
class RunnerCacheKeyTests(TestCase):
    """The key groups by exercise, not by student.

    That is the whole benefit for a class set: the second student's first
    batch reuses the solution pages the first student's batches warmed.
    """

    def make_check(self, solution_id, pages, student_id=1, name="Exercise 1.1"):
        return mock.Mock(solution_id=solution_id, solution_pages=pages,
                         student_id=student_id, exercise_name=name)

    def test_two_students_on_the_same_exercise_share_a_key(self):
        first = runner._cache_key(self.make_check(1, "2-12", student_id=1))
        second = runner._cache_key(self.make_check(1, "2-12", student_id=2))
        self.assertEqual(first, second)

    def test_a_different_page_range_gets_a_different_key(self):
        self.assertNotEqual(
            runner._cache_key(self.make_check(1, "2-12")),
            runner._cache_key(self.make_check(1, "17-21")),
        )

    def test_a_different_solutions_pdf_gets_a_different_key(self):
        self.assertNotEqual(
            runner._cache_key(self.make_check(1, "2-12")),
            runner._cache_key(self.make_check(2, "2-12")),
        )

    def test_a_different_exercise_name_gets_a_different_key(self):
        """The name is in the prompt, so it is part of the prefix."""
        self.assertNotEqual(
            runner._cache_key(self.make_check(1, "2-12", name="Exercise 1.1")),
            runner._cache_key(self.make_check(1, "2-12", name="Ex 1.1 Q1-8")),
        )

    def test_an_unscoped_check_still_produces_a_usable_key(self):
        self.assertIn("all", runner._cache_key(self.make_check(1, "")))

    def test_the_key_stays_within_what_analyse_chunk_will_send(self):
        """Truncated past 64 characters, which would silently merge groups."""
        key = runner._cache_key(self.make_check(1, "100-130", name="x" * 200))
        self.assertLessEqual(len(key), 64)
