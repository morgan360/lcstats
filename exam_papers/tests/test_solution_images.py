"""A part's marking scheme is one image; letter_region decides what it covers
when cut from the scheme PDF."""
from django.test import SimpleTestCase

from exam_papers.utils import letter_region


class LetterRegionTests(SimpleTestCase):
    def test_every_row_for_the_letter_is_covered(self):
        """The shape of 2025 P2 Q9(a): a "(a)(i)(ii)" row read as the whole
        letter, which used to hide the (ii) and (iv) rows behind it."""
        regions = {
            (9, 'a', None): {'slices': [(64, 62, 802), (65, 62, 256)], 'width': 595},
            (9, 'a', 'ii'): {'slices': [(64, 400, 802)], 'width': 595},
            (9, 'a', 'iv'): {'slices': [(65, 200, 700)], 'width': 595},
            (9, 'b', None): {'slices': [(65, 700, 802)], 'width': 595},
        }
        self.assertEqual(letter_region(regions, 9, 'a')['slices'],
                         [(64, 62, 802), (65, 62, 700)])

    def test_a_repeated_slice_is_cut_once(self):
        """2022 P2 Q8(a) listed the same strip of page 21 twice."""
        regions = {
            (8, 'a', None): {'slices': [(20, 72, 357), (21, 69, 106)], 'width': 595},
            (8, 'a', 'ii'): {'slices': [(20, 349, 802), (21, 69, 106)], 'width': 595},
        }
        self.assertEqual(letter_region(regions, 8, 'a')['slices'],
                         [(20, 72, 802), (21, 69, 106)])

    def test_rows_that_do_not_touch_stay_separate(self):
        """The gap between them is a table header, not part of the solution."""
        regions = {
            (5, 'a', 'i'): {'slices': [(10, 100, 200)], 'width': 595},
            (5, 'a', 'ii'): {'slices': [(10, 250, 300)], 'width': 600},
        }
        region = letter_region(regions, 5, 'a')
        self.assertEqual(region['slices'], [(10, 100, 200), (10, 250, 300)])
        self.assertEqual(region['width'], 600)

    def test_no_region_for_the_letter(self):
        self.assertIsNone(letter_region({}, 5, 'a'))
        self.assertIsNone(letter_region(None, 5, 'a'))
