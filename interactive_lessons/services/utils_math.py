import re
from sympy import simplify
from sympy.parsing.sympy_parser import (
    parse_expr, standard_transformations,
    implicit_multiplication_application, convert_xor
)
from sympy.parsing.latex import parse_latex
from sympy.core.sympify import SympifyError
from tokenize import TokenError

_TRANSFORMS = standard_transformations + (
    implicit_multiplication_application,
    convert_xor,
)

_DASHES = {
    "\u2212": "-",  # unicode minus
    "\u2013": "-",  # en dash
    "\u2014": "-",  # em dash
}

def _preclean_plain(expr: str) -> str:
    """Make text/MathLive-ish input safe for parse_expr (non-LaTeX path)."""
    if not expr:
        return ""

    # Trim and strip $ wrappers
    expr = expr.strip().strip("$")

    # Normalize double backslashes so we can inspect tokens sanely
    expr = expr.replace("\\\\", "\\")

    # ± and unicode dashes
    expr = expr.replace("±", "+-")
    expr = re.sub(r"(?i)plusminus", "+-", expr)
    for u, a in _DASHES.items():
        expr = expr.replace(u, a)

    # Common symbols
    expr = expr.replace("π", "pi")           # unicode pi → pi
    expr = expr.replace("\\pi", "pi")        # LaTeX \pi → pi (plain path)
    expr = expr.replace("°", "*pi/180")      # degrees → radians
    expr = expr.replace("\\times", "*").replace("\\cdot", "*")

    # Normalize roots to plain path if already plain-ish
    # (we leave true LaTeX \sqrt for the LaTeX path)
    expr = expr.replace("√(", "sqrt(")
    expr = re.sub(r"√([0-9a-zA-Z_]+)", r"sqrt(\1)", expr)
    expr = re.sub(r"(?i)squareroot", "sqrt", expr)

    # Remove LaTeX size wrappers if any crept in
    expr = re.sub(r"\\left|\\right", "", expr)
    expr = re.sub(r"^\\\(|\\\)$|^\\\[|\\\]$", "", expr)

    # Power & whitespace
    expr = expr.replace("^", "**")
    expr = re.sub(r"\s+", "", expr)

    # Curly braces to parens (harmless for plain parser)
    expr = expr.replace("{", "(").replace("}", ")")

    return expr

def _to_latex(expr: str) -> str:
    """Produce LaTeX the SymPy LaTeX parser will accept."""
    if not expr:
        return ""

    s = expr.strip().strip("$")
    s = s.replace("\\\\", "\\")  # collapse doubled slashes

    # Normalize unicode to LaTeX
    s = s.replace("π", r"\pi")
    # degrees: 45° → 45 * \pi / 180
    s = s.replace("°", r"*\pi/180")

    # Convert plain sqrt/Unicode √ to LaTeX \sqrt{...} when obvious
    # √(3) → \sqrt{3}
    s = s.replace("√(", r"\sqrt{(")  # temporary marker, fix next:
    s = re.sub(r"\\sqrt\{\(", r"\\sqrt{", s)
    s = s.replace(")}", "}")  # in case someone had nested braces

    # √3 → \sqrt{3}, √pi → \sqrt{\pi}
    s = re.sub(r"√\s*([0-9a-zA-Z]+)", r"\\sqrt{\1}", s)

    # If user wrote plain sqrt(...), keep it—LaTeX parser accepts \sqrt{} better,
    # so convert sqrt(x) → \sqrt{x}
    s = re.sub(r"sqrt\(([^()]+)\)", r"\\sqrt{\1}", s)

    # Make sure ^ stays LaTeX (no **)
    s = s.replace("**", "^")

    # Remove \left/\right which confuse some inputs
    s = re.sub(r"\\left|\\right", "", s)

    return s

def _parse_any(expr: str):
    """Try plain parser first; if it fails or looks LaTeX-y, fall back to parse_latex."""
    if not expr:
        raise SympifyError("empty")

    plain = _preclean_plain(expr)

    # Heuristic: if clearly LaTeX-ish, go straight to LaTeX
    looks_latex = bool(re.search(r"\\(frac|sqrt|pi)\b", expr)) or ("√" in expr)

    if not looks_latex:
        try:
            return parse_expr(plain, transformations=_TRANSFORMS)
        except (SympifyError, SyntaxError, TypeError, ValueError, TokenError):
            pass

    # LaTeX fallback
    try:
        latex_str = _to_latex(expr)
        return parse_latex(latex_str)
    except Exception as e:
        # last attempt: try plain again (after LaTeX normalization may have helped)
        return parse_expr(plain, transformations=_TRANSFORMS)

def compare_algebraic(student_ans: str, correct_ans: str) -> bool:
    """Return True if two algebraic expressions are equivalent."""
    if not student_ans or not correct_ans:
        return False
    try:
        s = _parse_any(student_ans)
        c = _parse_any(correct_ans)
        return simplify(s - c) == 0
    except (SympifyError, SyntaxError, TypeError, ValueError, TokenError):
        return False
