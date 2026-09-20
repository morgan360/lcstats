"""
Django management command to download Leaving Certificate Higher Level Mathematics papers and marking schemes.
Downloads papers from 2010-2025 and renames them to LC_HL_maths_Year_Px.pdf format.

With --deferred, downloads the deferred sitting instead, named
LC_HL_maths_Year_def_Px.pdf. Those papers have no predictable URL, so the
paths come from walking the archive's search form - see
exam_papers/services/sec_archive.py.

Usage: python manage.py download_lc_papers
       python manage.py download_lc_papers --deferred
"""

import os
import re
import requests
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from exam_papers.services import sec_archive

# A deferred fileid, e.g. LC003ALP100EV.pdf - higher level, paper 1, English
# version. Paper "0" is the marking scheme, level G is Ordinary.
FILEID_RE = re.compile(r'LC003(?P<level>[AG])LP(?P<paper>\d)00(?P<language>[EI])V\.pdf')


class Command(BaseCommand):
    help = 'Download LC Higher Level Maths papers and marking schemes from examinations.ie (2010-2025)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--start-year',
            type=int,
            default=2010,
            help='Starting year (default: 2010)'
        )
        parser.add_argument(
            '--end-year',
            type=int,
            default=2025,
            help='Ending year (default: 2025)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Print URLs without downloading'
        )
        parser.add_argument(
            '--papers-only',
            action='store_true',
            help='Download only exam papers (skip marking schemes)'
        )
        parser.add_argument(
            '--schemes-only',
            action='store_true',
            help='Download only marking schemes (skip exam papers)'
        )
        parser.add_argument(
            '--deferred',
            action='store_true',
            help="Download the deferred sitting instead of the main one. The "
                 "years on offer are read from the archive, so --start-year "
                 "and --end-year only narrow that list."
        )

    def handle(self, *args, **options):
        start_year = options['start_year']
        end_year = options['end_year']
        dry_run = options['dry_run']
        papers_only = options['papers_only']
        schemes_only = options['schemes_only']
        deferred = options['deferred']

        if papers_only and schemes_only:
            raise CommandError('--papers-only and --schemes-only contradict each other.')

        # Create output directory
        output_dir = os.path.join(settings.MEDIA_ROOT, 'exam_papers', 'lc_downloads')
        if not dry_run:
            os.makedirs(output_dir, exist_ok=True)
            self.stdout.write(f"Output directory: {output_dir}\n")

        if deferred:
            self.download_deferred(output_dir, start_year, end_year,
                                   dry_run, papers_only, schemes_only)
            return

        downloaded = 0
        failed = []

        # Download exam papers
        if not schemes_only:
            self.stdout.write(self.style.HTTP_INFO("\n📝 DOWNLOADING EXAM PAPERS\n"))
            papers_url_base = "https://www.examinations.ie/archive/exampapers"

            for year in range(start_year, end_year + 1):
                for paper in [1, 2]:
                    # URL pattern: https://www.examinations.ie/archive/exampapers/{YEAR}/LC003ALP{PAPER}00EV.pdf
                    url = f"{papers_url_base}/{year}/LC003ALP{paper}00EV.pdf"

                    # New filename format: LC_HL_maths_Year_Px.pdf
                    new_filename = f"LC_HL_maths_{year}_P{paper}.pdf"

                    if dry_run:
                        self.stdout.write(f"Would download: {url} -> {new_filename}")
                        continue

                    ok = self.fetch(url, os.path.join(output_dir, new_filename),
                                    f"{year} Paper {paper}", failed, (year, f"P{paper}"))
                    downloaded += ok

        # Download marking schemes
        if not papers_only:
            self.stdout.write(self.style.HTTP_INFO("\n📋 DOWNLOADING MARKING SCHEMES\n"))
            schemes_url_base = "https://www.examinations.ie/archive/markingschemes"

            for year in range(start_year, end_year + 1):
                # URL pattern: https://www.examinations.ie/archive/markingschemes/{YEAR}/LC003ALP000EV.pdf
                url = f"{schemes_url_base}/{year}/LC003ALP000EV.pdf"

                # New filename format: LC_HL_maths_Year_MS.pdf (MS = Marking Scheme)
                new_filename = f"LC_HL_maths_{year}_MS.pdf"

                if dry_run:
                    self.stdout.write(f"Would download: {url} -> {new_filename}")
                    continue

                ok = self.fetch(url, os.path.join(output_dir, new_filename),
                                f"{year} Marking Scheme", failed, (year, "MS"))
                downloaded += ok

        # Summary
        self.stdout.write("\n" + "="*60)
        if dry_run:
            total_count = 0
            if not schemes_only:
                total_count += (end_year - start_year + 1) * 2  # 2 papers per year
            if not papers_only:
                total_count += (end_year - start_year + 1)  # 1 marking scheme per year
            self.stdout.write(self.style.SUCCESS(f"Dry run complete. Would download {total_count} files."))
        else:
            self.report(downloaded, failed, output_dir)

    def fetch(self, url, output_path, label, failed, failure_key):
        """Download one file unless it is already there. Returns 1 if written."""
        new_filename = os.path.basename(output_path)

        if os.path.exists(output_path):
            self.stdout.write(self.style.WARNING(f"⏭️  Skipping {new_filename} (already exists)"))
            return 0

        try:
            self.stdout.write(f"📥 Downloading {label}...", ending=' ')
            response = requests.get(url, headers={'User-Agent': sec_archive.USER_AGENT},
                                    timeout=30)

            if response.status_code == 200:
                with open(output_path, 'wb') as f:
                    f.write(response.content)

                file_size = len(response.content) / 1024  # KB
                self.stdout.write(self.style.SUCCESS(f"✓ ({file_size:.1f} KB)"))
                return 1
            elif response.status_code == 404:
                self.stdout.write(self.style.WARNING("✗ (not found)"))
                failed.append((*failure_key, "404"))
            else:
                self.stdout.write(self.style.ERROR(f"✗ (status {response.status_code})"))
                failed.append((*failure_key, f"HTTP {response.status_code}"))

        except requests.exceptions.RequestException as e:
            self.stdout.write(self.style.ERROR(f"✗ (error: {str(e)[:50]})"))
            failed.append((*failure_key, str(e)[:50]))

        return 0

    def download_deferred(self, output_dir, start_year, end_year,
                          dry_run, papers_only, schemes_only):
        """Walk the archive form for the deferred sitting and fetch what it lists.

        Only Higher Level, English version is taken, matching the main
        download above.
        """
        views = []
        if not schemes_only:
            views.append((sec_archive.DEFERRED_PAPERS, "📝 DOWNLOADING DEFERRED EXAM PAPERS"))
        if not papers_only:
            views.append((sec_archive.DEFERRED_SCHEMES, "📋 DOWNLOADING DEFERRED MARKING SCHEMES"))

        downloaded = 0
        failed = []

        for view, heading in views:
            self.stdout.write(self.style.HTTP_INFO(f"\n{heading}\n"))

            try:
                years = sec_archive.years_available(view)
            except (requests.exceptions.RequestException, sec_archive.ArchiveError) as e:
                raise CommandError(f'Could not read the archive index: {e}')

            wanted = [y for y in years if start_year <= y <= end_year]
            if not wanted:
                self.stdout.write(self.style.WARNING(
                    f"   No deferred years between {start_year} and {end_year}. "
                    f"The archive offers: {', '.join(str(y) for y in years) or 'none'}"
                ))
                continue

            for year in sorted(wanted):
                try:
                    listed = sec_archive.list_files(view, year)
                except (requests.exceptions.RequestException, sec_archive.ArchiveError) as e:
                    self.stdout.write(self.style.ERROR(f"✗ {year}: {str(e)[:60]}"))
                    failed.append((year, view, str(e)[:50]))
                    continue

                if not listed:
                    self.stdout.write(self.style.WARNING(
                        f"⏭️  {year}: Maths not published for this sitting"))
                    continue

                for item in listed:
                    match = FILEID_RE.fullmatch(item['fileid'])
                    # Higher level, English version only.
                    if not match or match['level'] != 'A' or match['language'] != 'E':
                        continue

                    paper = match['paper']
                    suffix = 'MS' if paper == '0' else f'P{paper}'
                    new_filename = f"LC_HL_maths_{year}_def_{suffix}.pdf"
                    url = sec_archive.FILE_URL.format(path=item['path'])

                    if dry_run:
                        self.stdout.write(f"Would download: {url} -> {new_filename}")
                        continue

                    ok = self.fetch(url, os.path.join(output_dir, new_filename),
                                    f"{year} deferred {item['label']}",
                                    failed, (year, suffix))
                    downloaded += ok

        self.stdout.write("\n" + "=" * 60)
        if dry_run:
            self.stdout.write(self.style.SUCCESS("Dry run complete."))
        else:
            self.report(downloaded, failed, output_dir)

    def report(self, downloaded, failed, output_dir):
        self.stdout.write(self.style.SUCCESS(f"\n✓ Successfully downloaded: {downloaded} files"))

        if failed:
            self.stdout.write(self.style.WARNING(f"\n⚠️  Failed downloads: {len(failed)}"))
            for year, item_type, reason in failed:
                self.stdout.write(f"   - {year} {item_type}: {reason}")

        self.stdout.write(f"\n📁 Files saved to: {output_dir}")
