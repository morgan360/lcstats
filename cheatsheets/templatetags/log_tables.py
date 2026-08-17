from django import template

from cheatsheets import log_tables_index
from cheatsheets.views import get_log_tables_cheatsheet

register = template.Library()


@register.inclusion_tag('includes/log_tables_panel.html')
def log_tables_panel():
    """
    The floating log tables panel for question pages.

    Renders nothing if the booklet has not been uploaded, so a site without it
    simply has no button rather than a broken one.
    """
    cheatsheet = get_log_tables_cheatsheet()
    if not cheatsheet or not cheatsheet.pdf_file:
        return {'pdf_url': None}
    return log_tables_index.viewer_context(cheatsheet.pdf_file.url)
