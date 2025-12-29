"""
Manim Animation: Function Concepts - Input, Domain, Output, Range, Codomain
Created for NumScoil - LC Maths Interactive Learning Platform

This animation visually explains the key function concepts using sets and mappings.
"""

from manim import *
import sys
sys.path.append('/Users/morgan/django_projects/Manim')
from numscoil_core.theme import NumScoilScene

class FunctionConceptsAnimation(NumScoilScene):
    def construct(self):
        # NumScoil Brand Colors
        NUMSCOIL_BLUE = "#2E86AB"
        NUMSCOIL_ORANGE = "#F77F00"
        NUMSCOIL_TEAL = "#06A77D"
        NUMSCOIL_PURPLE = "#7209B7"
        NUMSCOIL_YELLOW = "#FCBF49"

        # Title with NumScoil branding
        title = Text("Function Concepts", font_size=48, color=NUMSCOIL_BLUE, weight=BOLD)
        subtitle = Text("Understanding Domain, Range & Codomain", font_size=24, color=NUMSCOIL_TEAL)
        subtitle.next_to(title, DOWN, buff=0.3)

        # NumScoil logo placeholder (you can replace with actual logo)
        logo = Text("NumScoil", font_size=20, color=NUMSCOIL_ORANGE, weight=BOLD)
        logo.to_corner(UR)

        self.play(Write(title), Write(subtitle), FadeIn(logo))
        self.wait(2)
        self.play(FadeOut(title), FadeOut(subtitle))
        self.wait(0.5)

        # =====================================================================
        # SCENE 1: Introduction to Sets
        # =====================================================================

        # Create two sets
        domain_set = Ellipse(width=3, height=4, color=NUMSCOIL_BLUE, fill_opacity=0.1)
        domain_set.shift(LEFT * 4)
        domain_label = Text("Set A\n(Domain)", font_size=24, color=NUMSCOIL_BLUE, weight=BOLD)
        domain_label.next_to(domain_set, UP, buff=0.3)

        codomain_set = Ellipse(width=3, height=4, color=NUMSCOIL_PURPLE, fill_opacity=0.1)
        codomain_set.shift(RIGHT * 4)
        codomain_label = Text("Set B\n(Codomain)", font_size=24, color=NUMSCOIL_PURPLE, weight=BOLD)
        codomain_label.next_to(codomain_set, UP, buff=0.3)

        # Function label
        function_label = MathTex(r"f: A \to B", font_size=36, color=NUMSCOIL_TEAL)
        function_label.move_to(UP * 3)

        self.play(
            Create(domain_set),
            Write(domain_label),
            Create(codomain_set),
            Write(codomain_label),
            Write(function_label)
        )
        self.wait(1)

        # =====================================================================
        # SCENE 2: Add Elements to Domain
        # =====================================================================

        # Domain elements (inputs)
        domain_elements = VGroup(
            Dot(point=domain_set.get_center() + UP * 1.2 + LEFT * 0.3, color=NUMSCOIL_BLUE, radius=0.15),
            Dot(point=domain_set.get_center() + UP * 0.4 + LEFT * 0.3, color=NUMSCOIL_BLUE, radius=0.15),
            Dot(point=domain_set.get_center() + DOWN * 0.4 + LEFT * 0.3, color=NUMSCOIL_BLUE, radius=0.15),
            Dot(point=domain_set.get_center() + DOWN * 1.2 + LEFT * 0.3, color=NUMSCOIL_BLUE, radius=0.15),
        )

        domain_numbers = VGroup(
            MathTex("1", font_size=28, color=WHITE).next_to(domain_elements[0], LEFT, buff=0.2),
            MathTex("2", font_size=28, color=WHITE).next_to(domain_elements[1], LEFT, buff=0.2),
            MathTex("3", font_size=28, color=WHITE).next_to(domain_elements[2], LEFT, buff=0.2),
            MathTex("4", font_size=28, color=WHITE).next_to(domain_elements[3], LEFT, buff=0.2),
        )

        domain_description = Text("Domain: All inputs", font_size=20, color=NUMSCOIL_BLUE)
        domain_description.next_to(domain_set, DOWN, buff=0.5)

        self.play(
            LaggedStart(*[GrowFromCenter(dot) for dot in domain_elements], lag_ratio=0.2),
            LaggedStart(*[Write(num) for num in domain_numbers], lag_ratio=0.2),
            Write(domain_description)
        )
        self.wait(1)

        # =====================================================================
        # SCENE 3: Define Function Rule
        # =====================================================================

        # Show function rule
        function_rule = MathTex(r"f(x) = x^2", font_size=36, color=NUMSCOIL_ORANGE)
        function_rule.move_to(UP * 2.5)

        self.play(Write(function_rule))
        self.wait(1)

        # =====================================================================
        # SCENE 4: Add Elements to Codomain (all possible outputs)
        # =====================================================================

        # Codomain elements (all possible outputs)
        codomain_elements = VGroup(
            Dot(point=codomain_set.get_center() + UP * 1.5 + RIGHT * 0.3, color=NUMSCOIL_PURPLE, radius=0.12),
            Dot(point=codomain_set.get_center() + UP * 1.0 + RIGHT * 0.3, color=NUMSCOIL_PURPLE, radius=0.12),
            Dot(point=codomain_set.get_center() + UP * 0.5 + RIGHT * 0.3, color=NUMSCOIL_PURPLE, radius=0.12),
            Dot(point=codomain_set.get_center() + UP * 0.0 + RIGHT * 0.3, color=NUMSCOIL_PURPLE, radius=0.12),
            Dot(point=codomain_set.get_center() + DOWN * 0.5 + RIGHT * 0.3, color=NUMSCOIL_PURPLE, radius=0.12),
            Dot(point=codomain_set.get_center() + DOWN * 1.0 + RIGHT * 0.3, color=NUMSCOIL_PURPLE, radius=0.12),
            Dot(point=codomain_set.get_center() + DOWN * 1.5 + RIGHT * 0.3, color=NUMSCOIL_PURPLE, radius=0.12),
        )

        codomain_numbers = VGroup(
            MathTex("0", font_size=24, color=WHITE).next_to(codomain_elements[0], RIGHT, buff=0.2),
            MathTex("1", font_size=24, color=WHITE).next_to(codomain_elements[1], RIGHT, buff=0.2),
            MathTex("4", font_size=24, color=WHITE).next_to(codomain_elements[2], RIGHT, buff=0.2),
            MathTex("9", font_size=24, color=WHITE).next_to(codomain_elements[3], RIGHT, buff=0.2),
            MathTex("16", font_size=24, color=WHITE).next_to(codomain_elements[4], RIGHT, buff=0.2),
            MathTex("25", font_size=24, color=WHITE).next_to(codomain_elements[5], RIGHT, buff=0.2),
            MathTex("...", font_size=24, color=WHITE).next_to(codomain_elements[6], RIGHT, buff=0.2),
        )

        codomain_description = Text("Codomain: All possible outputs", font_size=20, color=NUMSCOIL_PURPLE)
        codomain_description.next_to(codomain_set, DOWN, buff=0.5)

        self.play(
            LaggedStart(*[GrowFromCenter(dot) for dot in codomain_elements], lag_ratio=0.15),
            LaggedStart(*[Write(num) for num in codomain_numbers], lag_ratio=0.15),
            Write(codomain_description)
        )
        self.wait(1)

        # =====================================================================
        # SCENE 5: Show Mappings (Arrows)
        # =====================================================================

        # Create arrows from domain to codomain
        arrows = VGroup(
            Arrow(
                start=domain_elements[0].get_right(),
                end=codomain_elements[1].get_left(),
                color=NUMSCOIL_ORANGE,
                buff=0.1,
                stroke_width=3
            ),
            Arrow(
                start=domain_elements[1].get_right(),
                end=codomain_elements[2].get_left(),
                color=NUMSCOIL_ORANGE,
                buff=0.1,
                stroke_width=3
            ),
            Arrow(
                start=domain_elements[2].get_right(),
                end=codomain_elements[3].get_left(),
                color=NUMSCOIL_ORANGE,
                buff=0.1,
                stroke_width=3
            ),
            Arrow(
                start=domain_elements[3].get_right(),
                end=codomain_elements[4].get_left(),
                color=NUMSCOIL_ORANGE,
                buff=0.1,
                stroke_width=3
            ),
        )

        # Show calculations
        calculations = VGroup(
            MathTex(r"f(1) = 1^2 = 1", font_size=20, color=NUMSCOIL_YELLOW),
            MathTex(r"f(2) = 2^2 = 4", font_size=20, color=NUMSCOIL_YELLOW),
            MathTex(r"f(3) = 3^2 = 9", font_size=20, color=NUMSCOIL_YELLOW),
            MathTex(r"f(4) = 4^2 = 16", font_size=20, color=NUMSCOIL_YELLOW),
        )

        for i, calc in enumerate(calculations):
            calc.next_to(arrows[i], UP, buff=0.1)

        self.play(
            LaggedStart(*[GrowArrow(arrow) for arrow in arrows], lag_ratio=0.3),
            LaggedStart(*[Write(calc) for calc in calculations], lag_ratio=0.3),
        )
        self.wait(2)

        # =====================================================================
        # SCENE 6: Highlight Input and Output
        # =====================================================================

        # Highlight a specific input
        input_highlight = Circle(radius=0.3, color=NUMSCOIL_YELLOW, stroke_width=4)
        input_highlight.move_to(domain_elements[1])

        input_text = Text("Input", font_size=24, color=NUMSCOIL_YELLOW, weight=BOLD)
        input_text.next_to(input_highlight, LEFT, buff=0.5)

        self.play(Create(input_highlight), Write(input_text))
        self.wait(1)

        # Highlight corresponding output
        output_highlight = Circle(radius=0.3, color=NUMSCOIL_YELLOW, stroke_width=4)
        output_highlight.move_to(codomain_elements[2])

        output_text = Text("Output", font_size=24, color=NUMSCOIL_YELLOW, weight=BOLD)
        output_text.next_to(output_highlight, RIGHT, buff=0.5)

        self.play(Create(output_highlight), Write(output_text))
        self.wait(2)

        self.play(FadeOut(input_highlight), FadeOut(output_highlight),
                  FadeOut(input_text), FadeOut(output_text))

        # =====================================================================
        # SCENE 7: Highlight Range (actual outputs used)
        # =====================================================================

        # Highlight the range (actual outputs)
        range_highlights = VGroup(
            Circle(radius=0.25, color=NUMSCOIL_TEAL, stroke_width=4).move_to(codomain_elements[1]),
            Circle(radius=0.25, color=NUMSCOIL_TEAL, stroke_width=4).move_to(codomain_elements[2]),
            Circle(radius=0.25, color=NUMSCOIL_TEAL, stroke_width=4).move_to(codomain_elements[3]),
            Circle(radius=0.25, color=NUMSCOIL_TEAL, stroke_width=4).move_to(codomain_elements[4]),
        )

        range_description = Text("Range: Actual output values", font_size=20, color=NUMSCOIL_TEAL, weight=BOLD)
        range_description.move_to(DOWN * 3)

        self.play(
            LaggedStart(*[Create(highlight) for highlight in range_highlights], lag_ratio=0.2),
            Write(range_description)
        )
        self.wait(2)

        # =====================================================================
        # SCENE 8: Key Definitions Summary
        # =====================================================================

        # Fade out everything except logo
        self.play(
            *[FadeOut(mob) for mob in self.mobjects if mob != logo]
        )
        self.wait(0.5)

        # Create definition boxes
        definitions = VGroup(
            self.create_definition_box("Input", "An object put into the function", NUMSCOIL_ORANGE),
            self.create_definition_box("Domain", "Set of all inputs for which function is defined", NUMSCOIL_BLUE),
            self.create_definition_box("Output", "Object that comes out of the function", NUMSCOIL_YELLOW),
            self.create_definition_box("Range", "Set of actual output values", NUMSCOIL_TEAL),
            self.create_definition_box("Codomain", "Set of all possible output values", NUMSCOIL_PURPLE),
        )

        definitions.arrange(DOWN, buff=0.3, center=True)
        definitions.scale(0.8)

        self.play(LaggedStart(*[FadeIn(defn, shift=RIGHT) for defn in definitions], lag_ratio=0.3))
        self.wait(3)

        # Fade out definitions
        self.play(*[FadeOut(mob) for mob in self.mobjects if mob != self.footer])
        self.wait(0.5)

        # =====================================================================
        # SCENE 9: Standard NumScoil Closing Screen
        # =====================================================================

        # Show standard closing screen with scrolling tagline
        self.show_closing(wait_time=4, fade_out=True, show_tagline=True)

    def create_definition_box(self, term, definition, color):
        """Helper function to create a styled definition box"""
        # Create term text
        term_text = Text(term + ":", font_size=22, color=color, weight=BOLD)

        # Create definition text
        def_text = Text(definition, font_size=18, color=WHITE)
        def_text.next_to(term_text, RIGHT, buff=0.3)

        # Group them
        box_content = VGroup(term_text, def_text)

        # Create surrounding rectangle
        box = SurroundingRectangle(
            box_content,
            color=color,
            buff=0.2,
            corner_radius=0.1,
            stroke_width=2,
            fill_opacity=0.05
        )

        return VGroup(box, box_content)


# Render command:
# manim -pql function_concepts_animation.py FunctionConceptsAnimation