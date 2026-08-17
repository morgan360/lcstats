"""
Clickable contents for the Formulae and Tables booklet (media/cheatsheets/LogTables.pdf).

The booklet has no PDF bookmarks, so the links on its contents spread are added
here. This deliberately mirrors the printed contents *exactly* - the same 29
sections, the same wording, the same page numbers, in the same order - because
part of the point is that students learn their way around the real booklet they
will be handed in the exam. Nothing here is tailored to the student, the topic
or the subject.

The link areas are the rows of the contents spread itself (PDF pages 6 and 7),
stored as fractions of the displayed page so they scale with any zoom. They were
measured from the PDF's own text positions; see the note on rotation below.

If the booklet PDF is ever replaced with a different edition, re-measure the row
rectangles and re-check PAGE_OFFSET.
"""

import json

# Printed page 8 is the 9th page of the PDF, and the offset holds to the last
# numbered page (93 -> 94).
PAGE_OFFSET = 1

FIRST_PRINTED_PAGE = 8
LAST_PRINTED_PAGE = 93

# The booklet's contents spread. Every page in the PDF carries /Rotate 90, so the
# displayed page is landscape (595x420pt) even though the mediabox is portrait -
# the fractions below are in *displayed* space, which is what the viewer draws in.
CONTENTS_PDF_PAGES = (6, 7)
CONTENTS_PDF_PAGE = CONTENTS_PDF_PAGES[0]


def to_pdf_page(printed_page):
    """Printed booklet page number -> 1-based page in the PDF."""
    return printed_page + PAGE_OFFSET


def to_printed_page(pdf_page):
    """1-based page in the PDF -> printed booklet page number."""
    return pdf_page - PAGE_OFFSET


# Row rectangles on each contents page, as (printed page, title as printed in
# Irish, title as printed in English, x, y, width, height). The rectangle spans
# the whole row - Irish title, page number and English title - so the entire line
# is the click target.
_ROWS = {
    6: [
        (8, "Fad agus achar", "Length and area", 0.0672, 0.1713, 0.8655, 0.0453),
        (10, "Achar dromchla agus toirt", "Surface area and volume", 0.0672, 0.2181, 0.8655, 0.0453),
        (12, "Meastacháin ar achar", "Area approximations", 0.0672, 0.2650, 0.8655, 0.0453),
        (13, "Triantánacht", "Trigonometry", 0.0672, 0.3118, 0.8655, 0.0453),
        (17, "Céimseata", "Geometry", 0.0672, 0.3584, 0.8655, 0.0453),
        (18, "Céimseata chomhordanáideach", "Co-ordinate geometry", 0.0672, 0.4053, 0.8655, 0.0453),
        (20, "Ailgéabar", "Algebra", 0.0672, 0.4521, 0.8655, 0.0453),
        (21, "Séana agus logartaim", "Indices and logarithms", 0.0672, 0.4990, 0.8655, 0.0453),
        (22, "Seichimh agus sraitheanna", "Sequences and series", 0.0672, 0.5455, 0.8655, 0.0453),
        (23, "Tacair agus loighic", "Sets and logic", 0.0672, 0.5924, 0.8655, 0.0453),
        (25, "Calcalas", "Calculus", 0.0672, 0.6393, 0.8655, 0.0453),
        (28, "Eacnamaíocht", "Economics", 0.0672, 0.6861, 0.8655, 0.0453),
        (30, "Matamaitic an airgeadais", "Financial mathematics", 0.0672, 0.7327, 0.8655, 0.0453),
        (33, "Staitisticí agus dóchúlacht", "Statistics and probability", 0.0672, 0.7795, 0.8655, 0.0453),
        (44, "Aonaid tomhais", "Units of measurement", 0.0672, 0.8264, 0.8655, 0.0453),
    ],
    7: [
        (46, "Tairisigh bhunúsacha fhisiceacha", "Fundamental physical constants", 0.0672, 0.1713, 0.8655, 0.0453),
        (48, "Fisic cháithníní", "Particle physics", 0.0672, 0.2181, 0.8655, 0.0453),
        (50, "Meicnic", "Mechanics", 0.0672, 0.2650, 0.8655, 0.0453),
        (58, "Teas agus teocht", "Heat and temperature", 0.0672, 0.3118, 0.8655, 0.0453),
        (59, "Solas agus fuaim", "Light and sound", 0.0672, 0.3584, 0.8655, 0.0453),
        (60, "Optaic gheoiméadrach", "Geometric optics", 0.0672, 0.4053, 0.8655, 0.0453),
        (61, "Leictreachas", "Electricity", 0.0672, 0.4521, 0.8655, 0.0453),
        (63, "Radaighníomhaíocht", "Radioactivity", 0.0672, 0.4990, 0.8655, 0.0453),
        (64, "Ceimic", "Chemistry", 0.0672, 0.5455, 0.8655, 0.0453),
        # The only entry that wraps onto two lines, so its row is double height -
        # otherwise the first line would fall outside every link area.
        (65, "Siombailí do chainníochtaí fisiceacha coitianta agus na haonaid ina dtomhaistear iad",
         "Symbols and units of measurement of common physical quantities", 0.0672, 0.5924, 0.8655, 0.0753),
        (72, "Siombailí ciorcaid leictrigh", "Electrical circuit symbols", 0.0672, 0.6693, 0.8655, 0.0453),
        (79, "Na dúile", "The elements", 0.0672, 0.7161, 0.8655, 0.0453),
        (83, "Tábla na núiclídí", "Table of nuclides", 0.0672, 0.7630, 0.8655, 0.0453),
        (91, "Dúile, sórtáilte de réir na siombailí", "Elements, sorted by symbol", 0.0672, 0.8095, 0.8655, 0.0453),
    ],
}


def viewer_context(pdf_url, start_pdf_page=None):
    """
    Everything the viewer template needs, with the JavaScript-bound values
    already JSON-encoded.
    """
    return {
        'pdf_url': pdf_url,
        'start_pdf_page': start_pdf_page or CONTENTS_PDF_PAGE,
        'page_offset': PAGE_OFFSET,
        'first_printed_page': FIRST_PRINTED_PAGE,
        'last_printed_page': LAST_PRINTED_PAGE,
        'contents_pdf_page': CONTENTS_PDF_PAGE,
        'contents_pdf_pages': json.dumps(list(CONTENTS_PDF_PAGES)),
        'contents_links': json.dumps(get_contents_links()),
    }


def get_contents_links():
    """
    Link areas keyed by the PDF page they sit on, ready to be JSON-encoded for
    the viewer.
    """
    return {
        pdf_page: [
            {
                "printed_page": printed_page,
                "title_ga": title_ga,
                "title_en": title_en,
                "target": to_pdf_page(printed_page),
                "x": x,
                "y": y,
                "w": w,
                "h": h,
            }
            for printed_page, title_ga, title_en, x, y, w, h in rows
        ]
        for pdf_page, rows in _ROWS.items()
    }
