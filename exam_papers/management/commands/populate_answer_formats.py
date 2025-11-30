"""
Management command to populate common answer format templates.
Run this once after creating the AnswerFormatTemplate model.
"""
from django.core.management.base import BaseCommand
from exam_papers.models import AnswerFormatTemplate


class Command(BaseCommand):
    help = 'Populate common answer format templates'

    def handle(self, *args, **options):
        templates = [
            # Angles
            {
                'name': 'Degrees',
                'category': 'Angles',
                'description': 'Answer in degrees (e.g., 45° or 45)',
                'example': '45°',
                'order': 1
            },
            {
                'name': 'Radians',
                'category': 'Angles',
                'description': 'Answer in radians in terms of π (e.g., π/4)',
                'example': 'π/4',
                'order': 2
            },
            {
                'name': 'Decimal Degrees',
                'category': 'Angles',
                'description': 'Answer in degrees to 1 decimal place',
                'example': '45.5°',
                'order': 3
            },

            # Fractions
            {
                'name': 'Exact Fraction',
                'category': 'Fractions',
                'description': 'Give your answer as an exact fraction (e.g., 3/4)',
                'example': '3/4',
                'order': 10
            },
            {
                'name': 'Simplified Fraction',
                'category': 'Fractions',
                'description': 'Give your answer as a fraction in simplest form',
                'example': '2/3',
                'order': 11
            },
            {
                'name': 'Mixed Number',
                'category': 'Fractions',
                'description': 'Express as a mixed number (e.g., 2 1/2)',
                'example': '2 1/2',
                'order': 12
            },

            # Decimals
            {
                'name': 'Decimal (1dp)',
                'category': 'Decimals',
                'description': 'Answer to 1 decimal place',
                'example': '3.1',
                'order': 20
            },
            {
                'name': 'Decimal (2dp)',
                'category': 'Decimals',
                'description': 'Answer to 2 decimal places',
                'example': '3.14',
                'order': 21
            },
            {
                'name': 'Decimal (3dp)',
                'category': 'Decimals',
                'description': 'Answer to 3 decimal places',
                'example': '3.142',
                'order': 22
            },

            # Algebra
            {
                'name': 'Simplified Expression',
                'category': 'Algebra',
                'description': 'Simplify your answer fully',
                'example': 'x² + 2x - 3',
                'order': 30
            },
            {
                'name': 'Factored Form',
                'category': 'Algebra',
                'description': 'Express in factored form',
                'example': '(x + 3)(x - 1)',
                'order': 31
            },
            {
                'name': 'Expanded Form',
                'category': 'Algebra',
                'description': 'Express in expanded form',
                'example': 'x² + 5x + 6',
                'order': 32
            },
            {
                'name': 'Exact Surd Form',
                'category': 'Algebra',
                'description': 'Leave your answer in exact surd form',
                'example': '√2 + √3',
                'order': 33
            },

            # Coordinates
            {
                'name': 'Coordinate Point',
                'category': 'Coordinates',
                'description': 'Give coordinates in the form (x, y)',
                'example': '(3, 4)',
                'order': 40
            },
            {
                'name': 'Equation of Line',
                'category': 'Coordinates',
                'description': 'Give equation in the form y = mx + c',
                'example': 'y = 2x + 3',
                'order': 41
            },

            # Calculus
            {
                'name': 'Derivative',
                'category': 'Calculus',
                'description': 'Simplify your derivative fully',
                'example': '2x + 3',
                'order': 50
            },
            {
                'name': 'Integral with C',
                'category': 'Calculus',
                'description': 'Include the constant of integration + C',
                'example': 'x² + 3x + C',
                'order': 51
            },

            # Units
            {
                'name': 'Square Units',
                'category': 'Units',
                'description': 'Include units in your answer (cm², m², etc.)',
                'example': '25 cm²',
                'order': 60
            },
            {
                'name': 'Cubic Units',
                'category': 'Units',
                'description': 'Include units in your answer (cm³, m³, etc.)',
                'example': '125 cm³',
                'order': 61
            },
            {
                'name': 'Linear Units',
                'category': 'Units',
                'description': 'Include units in your answer (cm, m, etc.)',
                'example': '10 cm',
                'order': 62
            },

            # Probability & Statistics
            {
                'name': 'Probability Decimal',
                'category': 'Statistics',
                'description': 'Express as a decimal between 0 and 1',
                'example': '0.75',
                'order': 70
            },
            {
                'name': 'Probability Fraction',
                'category': 'Statistics',
                'description': 'Express as a fraction between 0 and 1',
                'example': '3/4',
                'order': 71
            },
            {
                'name': 'Percentage',
                'category': 'Statistics',
                'description': 'Express as a percentage',
                'example': '75%',
                'order': 72
            },

            # Sets
            {
                'name': 'Set Notation',
                'category': 'Sets',
                'description': 'Use set notation with curly braces',
                'example': '{1, 2, 3, 4}',
                'order': 80
            },
            {
                'name': 'Interval Notation',
                'category': 'Sets',
                'description': 'Use interval notation',
                'example': '[0, 5]',
                'order': 81
            },

            # Exact Values
            {
                'name': 'Exact Value (No Decimals)',
                'category': 'Exact',
                'description': 'Give an exact answer (no decimal approximations)',
                'example': '√2/2',
                'order': 90
            },
            {
                'name': 'In Terms of Pi',
                'category': 'Exact',
                'description': 'Leave your answer in terms of π',
                'example': '2π',
                'order': 91
            },
        ]

        created = 0
        updated = 0

        for template_data in templates:
            template, created_flag = AnswerFormatTemplate.objects.update_or_create(
                name=template_data['name'],
                defaults=template_data
            )
            if created_flag:
                created += 1
                self.stdout.write(self.style.SUCCESS(f'✓ Created: {template.name}'))
            else:
                updated += 1
                self.stdout.write(self.style.WARNING(f'⟳ Updated: {template.name}'))

        self.stdout.write(self.style.SUCCESS(f'\n=== Summary ==='))
        self.stdout.write(f'Created: {created} templates')
        self.stdout.write(f'Updated: {updated} templates')
        self.stdout.write(f'Total: {AnswerFormatTemplate.objects.count()} templates')
        self.stdout.write(self.style.SUCCESS('\n✓ Answer format templates ready to use!'))
        self.stdout.write('\nYou can now select these in the admin when creating question parts.')
