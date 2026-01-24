"""
Management command to scrape career guidance counsellor contact information from school websites.

Usage:
    python manage.py scrape_guidance_contacts
    python manage.py scrape_guidance_contacts --school-id 5
    python manage.py scrape_guidance_contacts --dry-run
"""

import re
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from django.core.management.base import BaseCommand
from schools.models import School


class Command(BaseCommand):
    help = 'Scrapes school websites to find career guidance counsellor contact information'

    def add_arguments(self, parser):
        parser.add_argument(
            '--school-id',
            type=int,
            help='Scrape only a specific school by ID'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without saving to database'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output'
        )

    def handle(self, *args, **options):
        """Main command handler."""

        school_id = options.get('school_id')
        dry_run = options.get('dry_run', False)
        verbose = options.get('verbose', False)

        # Get schools to scrape
        if school_id:
            schools = School.objects.filter(id=school_id)
        else:
            schools = School.objects.filter(website__isnull=False).exclude(website='')

        total_schools = schools.count()
        updated_count = 0
        failed_count = 0

        self.stdout.write(self.style.SUCCESS(f"\n{'='*70}"))
        self.stdout.write(self.style.SUCCESS(f"🔍 SCRAPING CAREER GUIDANCE CONTACTS"))
        self.stdout.write(self.style.SUCCESS(f"{'='*70}\n"))

        if dry_run:
            self.stdout.write(self.style.WARNING("🔸 DRY RUN MODE - No changes will be saved\n"))

        self.stdout.write(f"Schools to process: {total_schools}\n")

        for idx, school in enumerate(schools, 1):
            self.stdout.write(f"\n[{idx}/{total_schools}] Processing: {school.name}")

            if not school.website:
                self.stdout.write(self.style.WARNING("  ⊘ No website URL"))
                continue

            try:
                # Scrape the school website
                result = self.scrape_school_website(school.website, verbose)

                if result:
                    if verbose:
                        self.stdout.write(f"  ✓ Found: {result['name']}")
                        self.stdout.write(f"    Email: {result['email']}")
                        self.stdout.write(f"    Role: {result['role']}")

                    if not dry_run:
                        # Update school record
                        school.secondary_contact_name = result['name']
                        school.secondary_contact_email = result['email']
                        school.secondary_contact_role = result['role']
                        school.save()
                        self.stdout.write(self.style.SUCCESS(f"  ✓ Updated database"))
                    else:
                        self.stdout.write(self.style.WARNING(f"  ⊙ Would update (dry-run)"))

                    updated_count += 1
                else:
                    self.stdout.write(self.style.WARNING("  ⊘ No guidance contact found"))
                    failed_count += 1

                # Be nice to servers - delay between requests
                time.sleep(2)

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ✗ Error: {str(e)}"))
                failed_count += 1
                continue

        # Summary
        self.stdout.write(self.style.SUCCESS(f"\n{'='*70}"))
        self.stdout.write(self.style.SUCCESS(f"📊 SUMMARY"))
        self.stdout.write(self.style.SUCCESS(f"{'='*70}"))
        self.stdout.write(f"Total schools processed:  {total_schools}")
        self.stdout.write(self.style.SUCCESS(f"Successfully found:       {updated_count}"))
        self.stdout.write(self.style.WARNING(f"Not found/failed:         {failed_count}"))
        self.stdout.write(f"Success rate:             {updated_count/total_schools*100:.1f}%\n")

    def scrape_school_website(self, website_url, verbose=False):
        """
        Scrape a school website to find career guidance counsellor contact info.

        Returns:
            dict with 'name', 'email', 'role' if found, None otherwise
        """

        # Normalize URL
        if not website_url.startswith('http'):
            website_url = 'https://' + website_url

        # List of common page paths to check
        paths_to_check = [
            '',  # Homepage
            '/staff',
            '/staff.html',
            '/about/staff',
            '/our-staff',
            '/contact',
            '/contacts',
            '/guidance',
            '/student-services',
            '/student-support',
            '/career-guidance',
            '/staff-list',
            '/about-us/staff',
        ]

        # Keywords that indicate career guidance
        guidance_keywords = [
            'career guidance',
            'guidance counsellor',
            'guidance counselor',
            'careers guidance',
            'student counsellor',
            'student guidance',
        ]

        for path in paths_to_check:
            try:
                url = urljoin(website_url, path)

                if verbose:
                    print(f"    Checking: {url}")

                response = requests.get(url, timeout=10, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })

                if response.status_code != 200:
                    continue

                soup = BeautifulSoup(response.text, 'html.parser')

                # Search for guidance-related content
                page_text = soup.get_text().lower()

                # Check if page mentions career guidance
                has_guidance = any(keyword in page_text for keyword in guidance_keywords)

                if not has_guidance:
                    continue

                # Extract potential contacts
                result = self.extract_guidance_contact(soup, response.text)

                if result:
                    return result

            except requests.RequestException as e:
                if verbose:
                    print(f"    Error fetching {url}: {str(e)}")
                continue
            except Exception as e:
                if verbose:
                    print(f"    Error parsing {url}: {str(e)}")
                continue

        return None

    def extract_guidance_contact(self, soup, html_text):
        """
        Extract career guidance contact from page content.

        Returns:
            dict with 'name', 'email', 'role' or None
        """

        # Patterns to match
        guidance_keywords = [
            'career guidance',
            'guidance counsellor',
            'guidance counselor',
            'careers guidance',
        ]

        # Find all text blocks that mention guidance
        text = soup.get_text()
        lines = text.split('\n')

        # Look for email addresses near guidance keywords
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        name_pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b'  # Match proper names

        for i, line in enumerate(lines):
            line_lower = line.lower()

            # Check if this line mentions career guidance
            if any(keyword in line_lower for keyword in guidance_keywords):

                # Search nearby lines for email and name
                context_start = max(0, i - 3)
                context_end = min(len(lines), i + 4)
                context = '\n'.join(lines[context_start:context_end])

                # Find email
                emails = re.findall(email_pattern, context)

                if emails:
                    email = emails[0]

                    # Try to find name
                    names = re.findall(name_pattern, context)

                    # Filter out common false positives
                    valid_names = [
                        name for name in names
                        if len(name) > 5 and
                        'Career' not in name and
                        'Guidance' not in name and
                        'Student' not in name
                    ]

                    name = valid_names[0] if valid_names else "Career Guidance Counsellor"

                    # Determine role
                    if 'guidance counsellor' in line_lower or 'guidance counselor' in line_lower:
                        role = 'Guidance Counsellor'
                    elif 'career guidance' in line_lower:
                        role = 'Career Guidance'
                    else:
                        role = 'Student Support'

                    return {
                        'name': name,
                        'email': email,
                        'role': role
                    }

        # Alternative: Look for staff tables/lists
        tables = soup.find_all('table')
        for table in tables:
            table_text = table.get_text().lower()
            if any(keyword in table_text for keyword in guidance_keywords):
                # Extract email from this table
                emails = re.findall(email_pattern, str(table))
                if emails:
                    return {
                        'name': 'Career Guidance Counsellor',
                        'email': emails[0],
                        'role': 'Guidance Counsellor'
                    }

        return None
