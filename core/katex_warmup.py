"""Stop markdown-katex spawning a doomed node process on every LaTeX render.

markdown-katex renders maths by shelling out to a node 10 binary it bundles. To
discover which options that binary supports it runs it once with ``--help``,
piping stdout but leaving stderr inherited (``_get_cmd_help_text`` in
``markdown_katex/wrapper.py``). Under uWSGI stderr is a unix *datagram* socket,
a type node 10 cannot classify, so it dies during bootstrap with
ERR_UNKNOWN_STREAM_TYPE before printing anything - which is what fills the
production server log.

The probe swallows the failure: it returns an empty string, ``parse_options()``
ends up with an empty dict, and since only a non-empty dict counts as cached,
the probe runs again on the very next render. A 37 MB process is spawned and
killed for every piece of maths on the site, measured at ~75 ms per render on
production (263 ms vs 188 ms).

Running the probe once against a stderr node *can* classify fills the cache for
the life of the process. Rendered HTML is identical either way - this is purely
the cost of the failed lookup.
"""

import logging
import os

logger = logging.getLogger(__name__)


def warm_katex_options():
    """Populate markdown-katex's option cache. Returns True if it is warm.

    Best effort: this is an optimisation, so any failure is logged and
    swallowed rather than allowed to break startup.
    """
    try:
        from markdown_katex import wrapper
    except ImportError:
        return False

    # Private attributes, so tolerate them moving in a future release.
    parsed = getattr(wrapper, '_PARSED_OPTIONS', None)
    parse_options = getattr(wrapper, 'parse_options', None)
    if parsed is None or parse_options is None:
        logger.info("markdown-katex internals changed; skipping the options warm-up")
        return False
    if parsed:
        return True

    try:
        devnull = os.open(os.devnull, os.O_WRONLY)
    except OSError:
        return False

    saved = None
    try:
        saved = os.dup(2)
        os.dup2(devnull, 2)   # a character device, which node 10 is happy with
        parse_options()
    except Exception:
        logger.warning("Could not warm the markdown-katex option cache", exc_info=True)
    finally:
        if saved is not None:
            os.dup2(saved, 2)
            os.close(saved)
        os.close(devnull)

    return bool(getattr(wrapper, '_PARSED_OPTIONS', None))
