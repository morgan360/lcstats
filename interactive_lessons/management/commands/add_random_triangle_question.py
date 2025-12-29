"""
Management command to add the triangle geometry question to the Random section.
"""
from django.core.management.base import BaseCommand
from django.db import models
from interactive_lessons.models import Topic, Question, QuestionPart
import math


class Command(BaseCommand):
    help = 'Add triangle JKL and KML question to Random section'

    def handle(self, *args, **kwargs):
        # Get the Random topic
        topic = Topic.objects.get(name='Random')

        # Determine the next order number
        max_order = Question.objects.filter(topic=topic).aggregate(
            models.Max('order')
        )['order__max'] or 0
        next_order = max_order + 1

        # Solve the problem to get the answer
        # Triangle JKL: angles 69°, 50°, 19° at J, K, L; side JK = 10.7 m

        angle_J = 69
        angle_K_in_JKL = 50
        angle_L_in_JKL = 19
        JK = 10.7

        # Step 1: Find KL using sine rule in triangle JKL
        # JK / sin(L) = KL / sin(J)
        angle_J_rad = math.radians(angle_J)
        angle_L_in_JKL_rad = math.radians(angle_L_in_JKL)

        KL = JK * math.sin(angle_J_rad) / math.sin(angle_L_in_JKL_rad)
        # KL ≈ 30.76 m

        # Step 2: In triangle KML, we have:
        # - KL (calculated above) ≈ 30.76 m
        # - ML = 32.1 m
        # - We need to find angle KML

        ML = 32.1

        # Step 3: Use sine rule in triangle KML to find angle MKL first
        # We need one angle in triangle KML to proceed
        # From the diagram, since triangles share side KL and M is positioned above,
        # the angle at K in triangle KML would be: 180° - 50° = 130°
        # (supplementary to angle JKL)

        angle_MKL = 180 - angle_K_in_JKL  # 130°
        angle_MKL_rad = math.radians(angle_MKL)

        # Step 4: Use sine rule to find angle KML
        # KL / sin(∠KML) = ML / sin(∠MKL)
        # sin(∠KML) = KL × sin(∠MKL) / ML

        sin_angle_KML = KL * math.sin(angle_MKL_rad) / ML
        angle_KML_rad = math.asin(sin_angle_KML)
        angle_KML_deg = math.degrees(angle_KML_rad)

        # Step 5: Verify by calculating the third angle in triangle KML
        angle_MLK = 180 - angle_MKL - angle_KML_deg

        # Create the question
        question = Question.objects.create(
            topic=topic,
            order=next_order,
            section='Geometry - Triangles',
            hint='Use the sine rule to find side KL in triangle JKL first. Then recognize that angle MKL is supplementary to angle JKL, and use the sine rule again in triangle KML.',
        )

        # Create the question part
        QuestionPart.objects.create(
            question=question,
            label='',
            prompt='JKL and KML are triangles. Find the size of the angle KML. Give your answer to 2 significant figures.',
            answer=str(int(round(angle_KML_deg))),  # Store as integer degrees
            expected_format='degrees to 2 significant figures',
            expected_type='numeric',
            max_marks=10,
            solution=(
                '**Step 1:** Find side KL using the sine rule in triangle JKL.\n\n'
                'In triangle JKL:\n'
                '- Angle J = 69°\n'
                '- Angle JKL (at K) = 50°\n'
                '- Angle JLK (at L) = 19°\n'
                '- Side JK = 10.7 m\n\n'
                'Using the sine rule:\n'
                '$$\\frac{JK}{\\sin(\\angle JLK)} = \\frac{KL}{\\sin(\\angle J)}$$\n\n'
                '$$\\frac{10.7}{\\sin(19°)} = \\frac{KL}{\\sin(69°)}$$\n\n'
                f'$$KL = \\frac{{10.7 \\times \\sin(69°)}}{{\\sin(19°)}} ≈ {KL:.2f}\\text{{ m}}$$\n\n'
                '**Step 2:** Find angle MKL in triangle KML.\n\n'
                'Since the triangles share side KL and point M is on the opposite side of KL from point J,\n'
                'the angle MKL is supplementary to angle JKL:\n'
                f'$$\\angle MKL = 180° - \\angle JKL = 180° - 50° = {angle_MKL}°$$\n\n'
                '**Step 3:** Use the sine rule in triangle KML to find angle KML.\n\n'
                'In triangle KML we now have:\n'
                f'- Side KL ≈ {KL:.2f} m\n'
                '- Side ML = 32.1 m\n'
                f'- Angle MKL = {angle_MKL}°\n\n'
                'Using the sine rule:\n'
                '$$\\frac{KL}{\\sin(\\angle KML)} = \\frac{ML}{\\sin(\\angle MKL)}$$\n\n'
                f'$$\\sin(\\angle KML) = \\frac{{KL \\times \\sin({angle_MKL}°)}}{{ML}}$$\n\n'
                f'$$\\sin(\\angle KML) = \\frac{{{KL:.2f} \\times \\sin({angle_MKL}°)}}{{32.1}}$$\n\n'
                f'$$\\sin(\\angle KML) ≈ {sin_angle_KML:.4f}$$\n\n'
                f'$$\\angle KML = \\arcsin({sin_angle_KML:.4f}) ≈ {angle_KML_deg:.2f}°$$\n\n'
                f'**Answer:** {int(round(angle_KML_deg))}° (to 2 significant figures)'
            ),
            order=1
        )

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created question {next_order} in Random section with angle KML ≈ {angle_KML_deg:.2f}°'
            )
        )