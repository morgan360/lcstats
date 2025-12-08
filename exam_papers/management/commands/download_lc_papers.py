"""
Django management command to download Leaving Certificate Higher Level Mathematics papers and marking schemes.
Downloads papers from 2010-2025 and renames them to LC_HL_maths_Year_Px.pdf format.

Usage: python manage.py download_lc_papers
"""

import os
import requests
from django.core.management.base import BaseCommand
from django.conf import settings


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

    def handle(self, *args, **options):
        start_year = options['start_year']
        end_year = options['end_year']
        dry_run = options['dry_run']
        papers_only = options['papers_only']
        schemes_only = options['schemes_only']

        # Create output directory
        output_dir = os.path.join(settings.MEDIA_ROOT, 'exam_papers', 'lc_downloads')
        if not dry_run:
            os.makedirs(output_dir, exist_ok=True)
            self.stdout.write(f"Output directory: {output_dir}\n")

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
                    output_path = os.path.join(output_dir, new_filename)

                    if dry_run:
                        self.stdout.write(f"Would download: {url} -> {new_filename}")
                        continue

                    # Check if file already exists
                    if os.path.exists(output_path):
                        self.stdout.write(self.style.WARNING(f"⏭️  Skipping {new_filename} (already exists)"))
                        continue

                    # Download the file
                    try:
                        self.stdout.write(f"📥 Downloading {year} Paper {paper}...", ending=' ')
                        response = requests.get(url, timeout=30)

                        if response.status_code == 200:
                            # Save the file
                            with open(output_path, 'wb') as f:
                                f.write(response.content)

                            file_size = len(response.content) / 1024  # KB
                            self.stdout.write(self.style.SUCCESS(f"✓ ({file_size:.1f} KB)"))
                            downloaded += 1
                        elif response.status_code == 404:
                            self.stdout.write(self.style.WARNING(f"✗ (not found)"))
                            failed.append((year, f"P{paper}", "404"))
                        else:
                            self.stdout.write(self.style.ERROR(f"✗ (status {response.status_code})"))
                            failed.append((year, f"P{paper}", f"HTTP {response.status_code}"))

                    except requests.exceptions.RequestException as e:
                        self.stdout.write(self.style.ERROR(f"✗ (error: {str(e)[:50]})"))
                        failed.append((year, f"P{paper}", str(e)[:50]))

        # Download marking schemes
        if not papers_only:
            self.stdout.write(self.style.HTTP_INFO("\n📋 DOWNLOADING MARKING SCHEMES\n"))
            schemes_url_base = "https://www.examinations.ie/archive/markingschemes"

            for year in range(start_year, end_year + 1):
                # URL pattern: https://www.examinations.ie/archive/markingschemes/{YEAR}/LC003ALP000EV.pdf
                url = f"{schemes_url_base}/{year}/LC003ALP000EV.pdf"

                # New filename format: LC_HL_maths_Year_MS.pdf (MS = Marking Scheme)
                new_filename = f"LC_HL_maths_{year}_MS.pdf"
                output_path = os.path.join(output_dir, new_filename)

                if dry_run:
                    self.stdout.write(f"Would download: {url} -> {new_filename}")
                    continue

                # Check if file already exists
                if os.path.exists(output_path):
                    self.stdout.write(self.style.WARNING(f"⏭️  Skipping {new_filename} (already exists)"))
                    continue

                # Download the file
                try:
                    self.stdout.write(f"📥 Downloading {year} Marking Scheme...", ending=' ')
                    response = requests.get(url, timeout=30)

                    if response.status_code == 200:
                        # Save the file
                        with open(output_path, 'wb') as f:
                            f.write(response.content)

                        file_size = len(response.content) / 1024  # KB
                        self.stdout.write(self.style.SUCCESS(f"✓ ({file_size:.1f} KB)"))
                        downloaded += 1
                    elif response.status_code == 404:
                        self.stdout.write(self.style.WARNING(f"✗ (not found)"))
                        failed.append((year, "MS", "404"))
                    else:
                        self.stdout.write(self.style.ERROR(f"✗ (status {response.status_code})"))
                        failed.append((year, "MS", f"HTTP {response.status_code}"))

                except requests.exceptions.RequestException as e:
                    self.stdout.write(self.style.ERROR(f"✗ (error: {str(e)[:50]})"))
                    failed.append((year, "MS", str(e)[:50]))

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
            self.stdout.write(self.style.SUCCESS(f"\n✓ Successfully downloaded: {downloaded} files"))

            if failed:
                self.stdout.write(self.style.WARNING(f"\n⚠️  Failed downloads: {len(failed)}"))
                for year, item_type, reason in failed:
                    self.stdout.write(f"   - {year} {item_type}: {reason}")

            self.stdout.write(f"\n📁 Files saved to: {output_dir}")