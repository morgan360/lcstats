# exam_papers/services/sec_archive.py
"""Finding papers in the SEC's exam material archive at examinations.ie.

The ordinary papers and marking schemes sit at predictable URLs, so
``download_lc_papers`` builds those by hand. The *deferred* papers do not:
there is no directory listing (``/archive/deferredexams/`` answers 403), and
the only way to learn a file's path is to walk the archive's search form and
decode the obfuscated link it hands back.

The form is a chain of dropdowns, each of which posts the whole form back and
returns the next dropdown. Two details make it awkward to drive:

* Each ``<select>`` carries an ``onChange=SubmitForm("<token>")`` whose token
  goes into the posted URL as ``?i=<token>``. The tokens are regenerated per
  session, so they have to be scraped from the page rather than hardcoded.
* Each ``<select>`` has a hidden twin - ``sbh__<Name>`` beside ``sbv__<Name>`` -
  which must be posted too, or the choice does not stick and the next dropdown
  never appears.

The site answers 403 without a browser User-Agent and rate-limits to 429
readily, hence the header and the pause between requests.
"""
import re
import time

import requests

BASE_URL = 'https://www.examinations.ie/exammaterialarchive/index.php'
FILE_URL = 'https://www.examinations.ie/{path}'
USER_AGENT = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
              'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36')

# ViewType dropdown values.
DEFERRED_PAPERS = 'deferredexams'
DEFERRED_SCHEMES = 'deferredmarkingschemes'

# SubjectSelect value. The ids are the SEC's own and are stable across years.
SUBJECT_MATHS = '3'

FIELD = 'MaterialArchive__noTable__{kind}__{name}'

# One result row: the fileid, the human label, and the obfuscated path.
_ROW_RE = re.compile(
    r"name='fileid' value='([^']+)'>\s*<TR>\s*<TD class='materialbody'>(.*?)</TD>"
    r".*?\?fp=([0-9.]+)",
    re.S)
_SELECT_RE = re.compile(r'<select\b[^>]*name="([^"]+)"[^>]*>(.*?)</select>', re.I | re.S)
_OPTION_RE = re.compile(r'<option value="([^"]*)"[^>]*>([^<]*)')
_TOKEN_RE = re.compile(r'name="([^"]+)"[^>]*onChange=SubmitForm\("([^"]+)"\)')
_TAG_RE = re.compile(r'<[^>]+>')


class ArchiveError(RuntimeError):
    """The archive did not answer in the shape this module expects."""


def decode_fp(fp):
    """Turn a ``?fp=`` value into the file's path under examinations.ie.

    The value is the path with one constant added to every character code.
    The constant differs per link, but every path begins "archive/", so the
    first number pins it down.

    There is one junk character after the ".pdf" - a checksum of some kind -
    which has to come off or the URL 404s.
    """
    try:
        numbers = [int(n) for n in fp.split('.')]
    except ValueError:
        raise ArchiveError(f'Not an fp value: {fp!r}')
    if not numbers:
        raise ArchiveError('Empty fp value')

    offset = ord('a') - numbers[0]
    path = ''.join(chr(n + offset) for n in numbers)
    if not path.startswith('archive/'):
        raise ArchiveError(f'Decoded fp does not look like a path: {path!r}')
    return re.sub(r'\.pdf.*$', '.pdf', path)


class ArchiveSession:
    """A walk through the archive's dropdowns, one selection at a time."""

    def __init__(self, delay=2.0, timeout=30):
        self.delay = delay
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers['User-Agent'] = USER_AGENT
        self.fields = {}
        self.html = ''
        self.tokens = {}

    # -- driving the form ------------------------------------------------

    def _post(self, token=None):
        url = BASE_URL + (f'?i={token}' if token else '')
        response = self.session.post(url, data=self.fields, timeout=self.timeout)
        response.raise_for_status()
        self.html = response.text
        self.tokens = dict(_TOKEN_RE.findall(self.html))
        time.sleep(self.delay)

    def _token_for(self, name):
        for field, token in self.tokens.items():
            if field.endswith(f'__{name}'):
                return token
        raise ArchiveError(
            f'No submit token for {name} - the archive form has changed shape.')

    def open(self):
        """Accept the terms, which is what reveals the first dropdown."""
        self.fields[FIELD.format(kind='cbv', name='AgreeCheck')] = 'on'
        self.fields[FIELD.format(kind='cbh', name='AgreeCheck')] = 'Y'
        self._post()
        return self

    def select(self, name, value):
        """Answer one dropdown, which returns the next one."""
        token = self._token_for(name)
        self.fields[FIELD.format(kind='sbv', name=name)] = value
        self.fields[FIELD.format(kind='sbh', name=name)] = 'id'
        self._post(token)
        return self

    # -- reading the page ------------------------------------------------

    def options(self, name):
        """The {value: label} a dropdown is currently offering."""
        for field, body in _SELECT_RE.findall(self.html):
            if field.endswith(f'__{name}'):
                return {value: label.strip()
                        for value, label in _OPTION_RE.findall(body)
                        if value}
        return {}

    def results(self):
        """The files the current selection has produced."""
        return [{'fileid': fileid,
                 'label': _TAG_RE.sub('', label).strip(),
                 'path': decode_fp(fp)}
                for fileid, label, fp in _ROW_RE.findall(self.html)]


def years_available(view, delay=2.0):
    """The years the archive offers for a view, newest first."""
    archive = ArchiveSession(delay=delay).open().select('ViewType', view)
    years = sorted((y for y in archive.options('YearSelect') if y.isdigit()),
                   reverse=True)
    return [int(y) for y in years]


def list_files(view, year, subject=SUBJECT_MATHS, delay=2.0):
    """Every file the archive lists for one view, year and subject.

    Returns a list of {'fileid', 'label', 'path'}, empty if the subject was
    not examined - or not published - that year.
    """
    archive = (ArchiveSession(delay=delay).open()
               .select('ViewType', view)
               .select('YearSelect', str(year))
               .select('ExaminationSelect', 'lc'))

    if subject not in archive.options('SubjectSelect'):
        return []

    return archive.select('SubjectSelect', subject).results()


def download(path, timeout=60):
    """Fetch one archive file. Returns its bytes, or None if it is not a PDF."""
    response = requests.get(FILE_URL.format(path=path),
                            headers={'User-Agent': USER_AGENT},
                            timeout=timeout)
    if response.status_code != 200 or not response.content.startswith(b'%PDF'):
        return None
    return response.content
