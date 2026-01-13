"""
Management command to seed initial school contact data.
Usage: python manage.py seed_schools
"""

from django.core.management.base import BaseCommand
from schools.models import School


class Command(BaseCommand):
    help = 'Seeds the database with initial school contact information'

    def handle(self, *args, **options):
        """Populate database with initial school data from research."""

        schools_data = [
            {
                'name': 'Newbridge College',
                'principal_name': 'Mr. Patrick O\'Brien',
                'email': 'info@newbridge-college.ie',
                'phone': '+353 45 487200',
                'address': 'Newbridge, Co. Kildare',
                'county': 'Kildare',
                'school_type': 'secondary',
                'website': 'https://www.newbridgecollege.ie',
            },
            {
                'name': 'Blackrock College',
                'principal_name': 'Ms. Yvonne Markey',
                'email': 'info@blackrockcollege.com',
                'phone': '+353 1 275 2100',
                'address': 'Rock Road, Blackrock, Co. Dublin A94 FK84',
                'county': 'Dublin',
                'school_type': 'secondary',
                'website': 'https://www.blackrockcollege.com',
            },
            {
                'name': 'Castleknock College',
                'principal_name': 'Miss Elaine Kelly',
                'email': 'principalpa@castleknockcollege.ie',
                'phone': '',
                'address': 'Castleknock, Dublin',
                'county': 'Dublin',
                'school_type': 'secondary',
                'website': 'https://www.castleknockcollege.ie',
            },
            {
                'name': 'Coláiste Íosagáin',
                'principal_name': 'Treasa Ní Fhearraigh',
                'email': 'eolas@eoiniosagain.ie',
                'phone': '',
                'address': 'Stillorgan Road, Booterstown, Blackrock, Co. Dublin',
                'county': 'Dublin',
                'school_type': 'secondary',
                'website': '',
            },
            {
                'name': 'Christian Brothers College Cork',
                'principal_name': 'Mr. David Lordon',
                'email': 'enquire@cbccork.ie',
                'phone': '0214501653',
                'address': 'Sidney Hill, Wellington Road, Cork',
                'county': 'Cork',
                'school_type': 'secondary',
                'website': 'https://www.cbccork.ie',
            },
            {
                'name': 'Presentation Brothers College Cork',
                'principal_name': 'Mr. David Barry',
                'email': 'info@pbc-cork.ie',
                'phone': '021-4272743',
                'address': 'The Mardyke, Cork',
                'county': 'Cork',
                'school_type': 'secondary',
                'website': 'https://www.pbc-cork.ie',
            },
            {
                'name': 'Cork Educate Together Secondary School',
                'principal_name': 'Mr. Colm O\'Connor',
                'email': 'info@cetsl.ie',
                'phone': '',
                'address': 'Cork',
                'county': 'Cork',
                'school_type': 'secondary',
                'website': 'http://www.cetsl.ie',
            },
            {
                'name': 'St. Munchin\'s College',
                'principal_name': 'Mr. Shane Fitzgerald',
                'email': 'office@stmunchinscollege.ie',
                'phone': '061348922',
                'address': 'Corbally, Limerick',
                'county': 'Limerick',
                'school_type': 'secondary',
                'website': 'http://www.stmunchinscollege.com',
            },
            {
                'name': 'Ardscoil Rís Limerick',
                'principal_name': 'Mr. Tom Prendergast',
                'email': 'asroffice@eircom.net',
                'phone': '061-453828',
                'address': 'North Circular Road, Limerick V94 V602',
                'county': 'Limerick',
                'school_type': 'secondary',
                'website': 'https://www.ardscoil.com',
            },
            {
                'name': 'Coláiste Chiaráin Athlone',
                'principal_name': 'Mr. Brendan Waldron',
                'email': 'info@ccathlone.ie',
                'phone': '090 6492383',
                'address': 'Summerhill, Athlone, Co. Roscommon',
                'county': 'Roscommon',
                'school_type': 'secondary',
                'website': 'https://www.ccathlone.ie',
            },
            {
                'name': 'St Kieran\'s College Kilkenny',
                'principal_name': 'Mr. Adrian Finan',
                'email': 'school@stkieranscollege.ie',
                'phone': '0567761707',
                'address': 'College Road, Kilkenny',
                'county': 'Kilkenny',
                'school_type': 'secondary',
                'website': 'https://www.stkieranscollege.ie',
            },
            {
                'name': 'Galway City & Oranmore Educate Together Secondary School',
                'principal_name': 'Ms. Sarah Molloy',
                'email': 'admin@galwayetss.ie',
                'phone': '091 394262',
                'address': 'Newtownsmith, Galway City Centre, Galway',
                'county': 'Galway',
                'school_type': 'secondary',
                'website': 'https://galwayetss.ie',
            },
            {
                'name': 'Loreto College St Stephen\'s Green',
                'principal_name': 'Ms. Jacqueline Dempsey',
                'email': 'info@loretothegreen.ie',
                'phone': '016618179',
                'address': '53 St Stephens Green Dublin 2',
                'county': 'Dublin',
                'school_type': 'secondary',
                'website': 'https://www.loretothegreen.ie',
            },
            {
                'name': 'Gonzaga College',
                'principal_name': 'Mr. Damon McCaul',
                'email': 'headmaster@gonzaga.ie',
                'phone': '014972931',
                'address': 'Sandford Road, Ranelagh, Dublin 6',
                'county': 'Dublin',
                'school_type': 'secondary',
                'website': '',
            },
            {
                'name': 'Coláiste Eoin Finglas',
                'principal_name': 'Neil Dunphy',
                'email': 'info@eoin.cdetb.ie',
                'phone': '018341426',
                'address': 'Cappagh Road, Finglas West, Dublin 11',
                'county': 'Dublin',
                'school_type': 'secondary',
                'website': 'https://colaisteeoin.ie',
            },
            {
                'name': 'St Andrew\'s College Dublin',
                'principal_name': 'Ms Louise Marshall',
                'email': 'information@st-andrews.ie',
                'phone': '',
                'address': 'Dublin',
                'county': 'Dublin',
                'school_type': 'secondary',
                'website': 'https://www.sac.ie',
            },
            {
                'name': 'Mercy Mounthawk Secondary School',
                'principal_name': 'Mr. Patrick Fleming',
                'email': 'admin@mercymounthawk.ie',
                'phone': '066 710 2550',
                'address': 'Mounthawk, Tralee, Co. Kerry',
                'county': 'Kerry',
                'school_type': 'secondary',
                'website': 'https://mercymounthawk.ie',
            },
            {
                'name': 'Loreto Abbey Secondary School Dalkey',
                'principal_name': 'Mr. Robert Dunne',
                'email': 'principal@loretoabbeydalkey.ie',
                'phone': '012718900',
                'address': 'Loreto Avenue, Off Harbour Road, Dalkey, Co. Dublin A96 YC81',
                'county': 'Dublin',
                'school_type': 'secondary',
                'website': 'https://www.loretoabbeydalkey.com',
            },
            {
                'name': 'Coláiste Pobail Acla',
                'principal_name': 'Jason Ó Mongáin',
                'email': '[email protected]',
                'phone': '098 45139',
                'address': 'Polranny, Achill, Co. Mayo',
                'county': 'Mayo',
                'school_type': 'community',
                'website': 'https://colaistepobailacla.ie',
            },
            {
                'name': 'Presentation Secondary School Waterford',
                'principal_name': 'Ms. Sally Ronayne',
                'email': 'principal@preswaterford.ie',
                'phone': '051376584',
                'address': 'Cannon Street, Waterford',
                'county': 'Waterford',
                'school_type': 'secondary',
                'website': 'https://www.presentationsecondarywaterford.ie',
            },
        ]

        created_count = 0
        updated_count = 0

        for school_data in schools_data:
            school, created = School.objects.update_or_create(
                name=school_data['name'],
                defaults=school_data
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Created: {school.name}")
                )
            else:
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f"⟳ Updated: {school.name}")
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"\n{'='*50}\n"
                f"Summary:\n"
                f"  Created: {created_count} schools\n"
                f"  Updated: {updated_count} schools\n"
                f"  Total: {School.objects.count()} schools in database\n"
                f"{'='*50}"
            )
        )