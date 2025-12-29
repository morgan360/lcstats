"""
Management command to add perpendicular distance from point to line questions
Based on formula: d = |ax₁ + by₁ + c| / √(a² + b²)
"""

from django.core.management.base import BaseCommand
from interactive_lessons.models import Topic, Section, Question, QuestionPart
from django.core.files.base import ContentFile
import os
import matplotlib.pyplot as plt
import numpy as np
from io import BytesIO


class Command(BaseCommand):
    help = 'Add perpendicular distance from point to line questions'

    def generate_perpendicular_distance_diagram(self, a, b, c, x1, y1, filename):
        """
        Generate a diagram showing a point, line, and perpendicular distance.
        Line equation: ax + by + c = 0
        Point: (x1, y1)
        """
        fig, ax = plt.subplots(figsize=(10, 8))

        # Set up the plot range based on point location
        x_range = 8
        y_range = 8
        x_center = x1
        y_center = y1

        x_min = x_center - x_range
        x_max = x_center + x_range
        y_min = y_center - y_range
        y_max = y_center + y_range

        # Generate x values for plotting the line
        x_vals = np.linspace(x_min, x_max, 400)

        # Calculate y values from ax + by + c = 0 => y = -(ax + c)/b
        if b != 0:
            y_vals = -(a * x_vals + c) / b
        else:
            # Vertical line: x = -c/a
            x_line = -c / a
            ax.axvline(x=x_line, color='blue', linewidth=2, label=f'Line: ${a}x + {b}y + {c} = 0$')

        if b != 0:
            # Plot the line
            ax.plot(x_vals, y_vals, 'b-', linewidth=2, label=f'Line: ${a}x + {b}y + {c} = 0$')

        # Plot the point
        ax.plot(x1, y1, 'ro', markersize=10, label=f'Point $({x1}, {y1})$', zorder=5)

        # Find the foot of perpendicular
        # The perpendicular from (x1, y1) to ax + by + c = 0
        # has direction vector (a, b)
        # Foot of perpendicular: (x1, y1) + t(a, b) where t minimizes distance
        # t = -(ax1 + by1 + c)/(a^2 + b^2)
        t = -(a * x1 + b * y1 + c) / (a**2 + b**2)
        foot_x = x1 + t * a
        foot_y = y1 + t * b

        # Plot the foot of perpendicular
        ax.plot(foot_x, foot_y, 'go', markersize=8, label=f'Foot of perpendicular', zorder=5)

        # Draw the perpendicular line (dashed)
        ax.plot([x1, foot_x], [y1, foot_y], 'r--', linewidth=2, label='Perpendicular distance', zorder=4)

        # Calculate and display the distance
        distance = abs(a * x1 + b * y1 + c) / np.sqrt(a**2 + b**2)

        # Add distance annotation offset to the right of the perpendicular line
        mid_x = (x1 + foot_x) / 2
        mid_y = (y1 + foot_y) / 2

        # Offset the annotation to the right
        offset_x = mid_x + 1.5
        offset_y = mid_y

        ax.annotate(f'd = {distance:.2f}',
                   xy=(mid_x, mid_y),
                   xytext=(offset_x, offset_y),
                   fontsize=12,
                   bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.7),
                   ha='left',
                   arrowprops=dict(arrowstyle='->', color='black', lw=1))

        # Set equal aspect ratio and add grid
        ax.set_aspect('equal', adjustable='box')

        # Major grid lines
        ax.grid(True, which='major', linestyle='-', linewidth=0.8, color='gray', alpha=0.6)

        # Minor grid lines
        ax.minorticks_on()
        ax.grid(True, which='minor', linestyle=':', linewidth=0.5, color='gray', alpha=0.4)

        # Axes
        ax.axhline(y=0, color='black', linewidth=1.5)
        ax.axvline(x=0, color='black', linewidth=1.5)

        # Set limits
        ax.set_xlim(x_min, x_max)
        ax.set_ylim(y_min, y_max)

        # Labels and legend
        ax.set_xlabel('x', fontsize=12)
        ax.set_ylabel('y', fontsize=12)
        ax.set_title('Perpendicular Distance from Point to Line', fontsize=14, fontweight='bold')
        ax.legend(loc='best', fontsize=10)

        # Save to BytesIO
        buffer = BytesIO()
        plt.tight_layout()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        plt.close()
        buffer.seek(0)

        return buffer

    def handle(self, *args, **kwargs):
        # Get the topic
        topic = Topic.objects.get(name="The Line")

        # Create new section
        section, created = Section.objects.get_or_create(
            topic=topic,
            name="Perpendicular Distance from a Point to a Line",
            defaults={'order': 7}
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f'Created section: {section.name}'))
        else:
            self.stdout.write(self.style.WARNING(f'Section already exists: {section.name}'))

        # Question 1: Basic calculation
        q1 = Question.objects.create(
            section=section,
            topic=topic,
            order=1
        )

        # Generate diagram for Q1
        diagram_buffer = self.generate_perpendicular_distance_diagram(
            a=3, b=4, c=-10, x1=2, y1=3, filename='perp_dist_q1.png'
        )

        q1_part = QuestionPart.objects.create(
            question=q1,
            label='',
            prompt="Find the perpendicular distance from the point (2, 3) to the line \\(3x + 4y - 10 = 0\\).",
            answer="1.6",
            expected_type='numeric',
            max_marks=10,
            solution="""Using the formula \\(d = \\dfrac{|ax_1 + by_1 + c|}{\\sqrt{a^2 + b^2}}\\):

The line is \\(3x + 4y - 10 = 0\\), so \\(a = 3\\), \\(b = 4\\), \\(c = -10\\).

The point is \\((2, 3)\\), so \\(x_1 = 2\\), \\(y_1 = 3\\).

$$d = \\dfrac{|3(2) + 4(3) - 10|}{\\sqrt{3^2 + 4^2}}$$

$$d = \\dfrac{|6 + 12 - 10|}{\\sqrt{9 + 16}}$$

$$d = \\dfrac{|8|}{\\sqrt{25}}$$

$$d = \\dfrac{8}{5} = 1.6$$""",
            order=1
        )

        # Attach diagram to solution
        q1_part.solution_image.save(
            'perpendicular_distance_q1.png',
            ContentFile(diagram_buffer.read()),
            save=True
        )
        self.stdout.write(self.style.SUCCESS('Generated diagram for Q1'))

        # Question 2: Point on origin side
        q2 = Question.objects.create(
            section=section,
            topic=topic,
            order=2
        )

        # Generate diagram for Q2
        diagram_buffer = self.generate_perpendicular_distance_diagram(
            a=5, b=-12, c=7, x1=1, y1=-2, filename='perp_dist_q2.png'
        )

        q2_part = QuestionPart.objects.create(
            question=q2,
            label='',
            prompt="Find the perpendicular distance from the point (1, -2) to the line \\(5x - 12y + 7 = 0\\).",
            answer="2.77",
            expected_type='numeric',
            max_marks=10,
            solution="""Using the formula \\(d = \\dfrac{|ax_1 + by_1 + c|}{\\sqrt{a^2 + b^2}}\\):

The line is \\(5x - 12y + 7 = 0\\), so \\(a = 5\\), \\(b = -12\\), \\(c = 7\\).

The point is \\((1, -2)\\), so \\(x_1 = 1\\), \\(y_1 = -2\\).

$$d = \\dfrac{|5(1) + (-12)(-2) + 7|}{\\sqrt{5^2 + (-12)^2}}$$

$$d = \\dfrac{|5 + 24 + 7|}{\\sqrt{25 + 144}}$$

$$d = \\dfrac{|36|}{\\sqrt{169}}$$

$$d = \\dfrac{36}{13} \\approx 2.77$$""",
            order=1
        )

        # Attach diagram to solution
        q2_part.solution_image.save(
            'perpendicular_distance_q2.png',
            ContentFile(diagram_buffer.read()),
            save=True
        )
        self.stdout.write(self.style.SUCCESS('Generated diagram for Q2'))

        # Question 3: Convert to standard form first
        q3 = Question.objects.create(
            section=section,
            topic=topic,
            order=3
        )

        # Generate diagram for Q3 (convert y = 2x + 3 to 2x - y + 3 = 0)
        diagram_buffer = self.generate_perpendicular_distance_diagram(
            a=2, b=-1, c=3, x1=-1, y1=4, filename='perp_dist_q3.png'
        )

        q3_part = QuestionPart.objects.create(
            question=q3,
            label='',
            prompt="Find the perpendicular distance from the point (-1, 4) to the line with equation \\(y = 2x + 3\\).",
            answer="1.34",
            expected_type='numeric',
            max_marks=15,
            solution="""First, convert \\(y = 2x + 3\\) to standard form:

$$y = 2x + 3$$

$$2x - y + 3 = 0$$

So \\(a = 2\\), \\(b = -1\\), \\(c = 3\\).

The point is \\((-1, 4)\\), so \\(x_1 = -1\\), \\(y_1 = 4\\).

Using the formula:

$$d = \\dfrac{|2(-1) + (-1)(4) + 3|}{\\sqrt{2^2 + (-1)^2}}$$

$$d = \\dfrac{|-2 - 4 + 3|}{\\sqrt{4 + 1}}$$

$$d = \\dfrac{|-3|}{\\sqrt{5}}$$

$$d = \\dfrac{3}{\\sqrt{5}} = \\dfrac{3\\sqrt{5}}{5} \\approx 1.34$$""",
            order=1
        )

        # Attach diagram to solution
        q3_part.solution_image.save(
            'perpendicular_distance_q3.png',
            ContentFile(diagram_buffer.read()),
            save=True
        )
        self.stdout.write(self.style.SUCCESS('Generated diagram for Q3'))

        self.stdout.write(self.style.SUCCESS(f'Successfully created 3 perpendicular distance questions'))
        self.stdout.write(self.style.SUCCESS(f'Section: {section.name}'))
        self.stdout.write(self.style.SUCCESS(f'Questions: {Question.objects.filter(section=section).count()}'))
