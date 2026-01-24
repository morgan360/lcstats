#!/usr/bin/env python3
"""
Test the school website scraper on a few sample schools.
This helps verify it works before running on all schools.

Usage:
    python test_scraper.py
"""

import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lcaim.settings')
django.setup()

from schools.models import School
import requests
from bs4 import BeautifulSoup
import re

def test_school_scraping(school):
    """Test scraping a single school."""

    print(f"\n{'='*70}")
    print(f"Testing: {school.name}")
    print(f"Website: {school.website}")
    print(f"{'='*70}")

    if not school.website:
        print("❌ No website URL")
        return

    # Normalize URL
    url = school.website
    if not url.startswith('http'):
        url = 'https://' + url

    try:
        # Fetch homepage
        print(f"\n📥 Fetching: {url}")
        response = requests.get(url, timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

        print(f"✓ Status: {response.status_code}")

        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')

        # Look for guidance-related keywords
        text = soup.get_text().lower()

        guidance_keywords = [
            'career guidance',
            'guidance counsellor',
            'guidance counselor',
            'careers guidance',
        ]

        print(f"\n🔍 Searching for guidance keywords...")
        for keyword in guidance_keywords:
            if keyword in text:
                print(f"  ✓ Found: '{keyword}'")

        # Look for email addresses
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, response.text)

        if emails:
            print(f"\n📧 Found {len(emails)} email address(es):")
            for email in emails[:10]:  # Show first 10
                print(f"  • {email}")
        else:
            print(f"\n❌ No email addresses found")

        # Look for common staff page links
        print(f"\n🔗 Looking for staff page links...")
        staff_keywords = ['staff', 'contact', 'guidance', 'about']

        links = soup.find_all('a', href=True)
        for link in links:
            href = link.get('href', '').lower()
            text = link.get_text().lower()

            if any(keyword in href or keyword in text for keyword in staff_keywords):
                full_url = requests.compat.urljoin(url, link['href'])
                print(f"  • {link.get_text().strip()}: {full_url}")

    except Exception as e:
        print(f"❌ Error: {str(e)}")

def main():
    """Run tests on sample schools."""

    print("="*70)
    print("🧪 SCHOOL WEBSITE SCRAPER - TEST MODE")
    print("="*70)

    # Get schools with websites
    schools = School.objects.filter(
        website__isnull=False
    ).exclude(
        website=''
    )[:5]  # Test first 5 schools

    print(f"\nTesting {schools.count()} schools with websites...\n")

    for school in schools:
        test_school_scraping(school)
        print("\n" + "="*70)
        input("Press Enter to test next school (or Ctrl+C to stop)...")

    print("\n✅ Testing complete!")
    print("\nIf the scraper is finding guidance-related content and emails,")
    print("you can run the full scraper with:")
    print("  python manage.py scrape_guidance_contacts --dry-run")

if __name__ == '__main__':
    main()