"""The private storage guarantees, tested directly.

Both of these were real bugs before they were tests. FileSystemStorage falls
back to MEDIA_URL when base_url is None, so .url() cheerfully returned a public
/media/ path for a file that must never have one; and reading the location in
__init__ baked it in at import, so override_settings silently did nothing and
tests wrote to the real directory.
"""
from django.test import SimpleTestCase, override_settings

from students.storage import private_storage


class PrivateStorageTests(SimpleTestCase):
    def test_url_always_raises(self):
        with self.assertRaises(ValueError):
            private_storage.url("work/1/photo.jpg")

    def test_location_is_not_under_media_root(self):
        from django.conf import settings
        self.assertFalse(
            str(private_storage.location).startswith(str(settings.MEDIA_ROOT)),
            "private storage is inside the publicly served media directory",
        )

    def test_location_follows_the_setting_at_access_time(self):
        with override_settings(PRIVATE_MEDIA_ROOT="/tmp/numscoil-private-test"):
            self.assertEqual(private_storage.location, "/tmp/numscoil-private-test")
        self.assertNotEqual(private_storage.location, "/tmp/numscoil-private-test")
