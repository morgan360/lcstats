"""Storage for files that must not be publicly reachable.

Everything else the site stores -- question images, marking schemes, videos --
lives under MEDIA_ROOT, which in production is a web-server static mapping.
Requests for it never reach Django, so it cannot be permission-checked. That is
fine for exam papers and wrong for a photograph of a student's own work.

Files saved through private_storage land outside that mapping and are only
served by students.views_work.work_photo, which checks who is asking.
"""
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.utils.functional import cached_property


class PrivateStorage(FileSystemStorage):
    """FileSystemStorage rooted at PRIVATE_MEDIA_ROOT, with no public URL."""

    # Read at access time rather than in __init__, so the location is not baked
    # in at import. That is what makes override_settings work in tests -- and a
    # test that silently keeps writing to the real directory is worse than no
    # test at all.
    @cached_property
    def base_location(self):
        return settings.PRIVATE_MEDIA_ROOT

    @cached_property
    def location(self):
        return str(self.base_location)

    def url(self, name):
        """Always raises. There is deliberately no URL for these files.

        Passing base_url=None is not enough: FileSystemStorage falls back to
        MEDIA_URL, so .url() would happily return /media/work/... -- a public
        path for a file that must never have one. A template that tries to
        render one of these as an <img src> should fail loudly in development
        rather than emit that.
        """
        raise ValueError(
            f"{name!r} is private and has no URL. "
            "Serve it through the work_photo view, which checks ownership."
        )

    def _clear_cached_properties(self, setting, **kwargs):
        super()._clear_cached_properties(setting, **kwargs)
        if setting == "PRIVATE_MEDIA_ROOT":
            self.__dict__.pop("base_location", None)
            self.__dict__.pop("location", None)


private_storage = PrivateStorage()
