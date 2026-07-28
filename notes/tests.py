from unittest.mock import patch

import numpy as np
from django.test import TestCase

from notes.models import Note
from notes.utils import search_similar

FAKE_VEC = [1.0, 0.0, 0.0]


class SearchSimilarScopingTests(TestCase):
    """
    Note.save() calls the OpenAI embeddings API live, so these tests create
    notes via bulk_create (bypassing save()) with a hand-set embedding, and
    patch get_query_embedding so no real API call happens either.
    """

    @classmethod
    def setUpTestData(cls):
        cls.general_note = Note(
            title="General maths note", content="c", content_type="general",
            audience="all", embedding=FAKE_VEC,
        )
        cls.student_help = Note(
            title="Student site-help note", content="c", content_type="site_help",
            audience="student", embedding=FAKE_VEC,
        )
        cls.teacher_help = Note(
            title="Teacher site-help note", content="c", content_type="site_help",
            audience="teacher", embedding=FAKE_VEC,
        )
        cls.all_audience_help = Note(
            title="Everyone site-help note", content="c", content_type="site_help",
            audience="all", embedding=FAKE_VEC,
        )
        Note.objects.bulk_create(
            [cls.general_note, cls.student_help, cls.teacher_help, cls.all_audience_help]
        )

    def test_content_type_filter_excludes_general_notes(self):
        with patch("notes.utils.get_query_embedding", return_value=np.array(FAKE_VEC, dtype=np.float32)):
            results = search_similar("how do I", content_type="site_help", audience="teacher")
        titles = {n.title for _, n in results}
        self.assertIn(self.teacher_help.title, titles)
        self.assertIn(self.all_audience_help.title, titles)
        self.assertNotIn(self.student_help.title, titles)
        self.assertNotIn(self.general_note.title, titles)

    def test_audience_filter_for_student(self):
        with patch("notes.utils.get_query_embedding", return_value=np.array(FAKE_VEC, dtype=np.float32)):
            results = search_similar("how do I", content_type="site_help", audience="student")
        titles = {n.title for _, n in results}
        self.assertIn(self.student_help.title, titles)
        self.assertIn(self.all_audience_help.title, titles)
        self.assertNotIn(self.teacher_help.title, titles)

    def test_scoped_search_with_no_matches_returns_empty_not_crash(self):
        Note.objects.all().delete()
        with patch("notes.utils.get_query_embedding", return_value=np.array(FAKE_VEC, dtype=np.float32)):
            results = search_similar("anything", content_type="site_help", audience="student")
        self.assertEqual(results, [])
