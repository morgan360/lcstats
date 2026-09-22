"""A version stamp for static files, so a rebuilt asset actually reaches people.

`tailwind.css` is served from one unchanging URL, so a browser -- and
Cloudflare in front of it -- will happily keep yesterday's copy. That is not a
cosmetic problem: the stamp cards are drawn with Tailwind's fill- and stroke-
utilities, so an old stylesheet renders them as nothing at all, on a page that
otherwise looks completely normal.

Appending the file's modification time makes each build a new URL. It is read
once per process and cached, so this costs one stat per asset per reload.
"""
import logging
import os

from django import template
from django.contrib.staticfiles import finders
from django.contrib.staticfiles.storage import staticfiles_storage

logger = logging.getLogger(__name__)
register = template.Library()

_cache = {}


@register.simple_tag
def asset_version(path):
    """Seconds-since-epoch of that static file's last change, or '' if unknown.

    Never raises: a missing file must not take a page down over a cache hint.
    """
    if path in _cache:
        return _cache[path]

    stamp = ''
    try:
        # collectstatic'd copy first: that is what production serves.
        full_path = staticfiles_storage.path(path)
        if not os.path.exists(full_path):
            full_path = finders.find(path)
        if full_path and os.path.exists(full_path):
            stamp = str(int(os.path.getmtime(full_path)))
    except (NotImplementedError, ValueError, OSError) as exc:
        logger.warning("No version stamp for %s: %s", path, exc)

    _cache[path] = stamp
    return stamp
