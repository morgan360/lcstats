import re
from typing import List, Tuple

SANITIZER_VERSION = "1.0.8"  # sanity check

# ---------- helpers ----------
def _inline(tok: str) -> str:
    tok = tok.strip()
    # Balance a missing closing brace in tokens like \sigma_{\bar{x}
    if tok.count("{") > tok.count("}"):
        tok = tok + "}"
    return r"\(" + tok + r"\)"  # no spaces inside delimiters

# Recognise common math tokens
MATH_TOKENS = [
    r"\\[A-Za-z]+[A-Za-z0-9_{}^\\]*",          # \sigma, \bar{x}, \sigma_{\bar{x}}, ...
    r"[A-Za-z](?:_\{?[A-Za-z0-9\\]+\}?)*\d*",  # n, p, z, x1, x_1
]

CODE_FENCE_RE  = re.compile(r"(```[\s\S]*?```)", re.MULTILINE)
DISPLAYMATH_RE = re.compile(r"\$\$[\s\S]*?\$\$", re.MULTILINE)
INLINEMATH_RE  = re.compile(r"\\\([\s\S]*?\\\)")

# Plain parenthesised tokens to turn into inline math: (\sigma), (\sigma_{\bar{x}}), (n)
PARENS_MATH_RE = re.compile(r"\(\s*(" + "|".join(MATH_TOKENS) + r")\s*\)")

# Item matcher for run-on "where:" lines; supports raw () and already-inline \( \)
# (We keep this strict; we will "heal" unclosed \( ... before using it.)
INLINE_ITEM_RE = re.compile(
    r"-\s*(?:\(\s*(" + "|".join(MATH_TOKENS) + r")\s*\)|\\\(\s*(" + "|".join(MATH_TOKENS) + r")\s*\\\))\s*(?:is|=|:)?\s*",
    flags=re.IGNORECASE,
)

def _escape_percent_in_display(s: str) -> str:
    return s.replace("%", r"\%")

# ---------- protect/restore math ----------
def _protect_math(s: str) -> Tuple[str, List[str], List[str]]:
    displays: List[str] = []
    inlines:  List[str] = []

    def sub_display(m):
        displays.append(m.group(0))
        return f"@@DMATH_{len(displays)-1}@@"

    def sub_inline(m):
        inlines.append(m.group(0))
        return f"@@IMATH_{len(inlines)-1}@@"

    s = DISPLAYMATH_RE.sub(sub_display, s)
    s = INLINEMATH_RE.sub(sub_inline, s)
    return s, displays, inlines

def _restore_math(s: str, displays: List[str], inlines: List[str]) -> str:
    s = re.sub(r"@@IMATH_(\d+)@@", lambda m: inlines[int(m.group(1))], s)
    s = re.sub(r"@@DMATH_(\d+)@@", lambda m: displays[int(m.group(1))], s)
    return s

# ---------- where: helpers ----------
_HEAL_UNCLOSED_INLINE_BEFORE_SEP = [
    # close missing '}' AND '\)' before separators (=, :, 'is')
    (re.compile(r"(\\\([^)]*?_\{[^}]*)(?=\s*(?:=|:|is)\b)", re.IGNORECASE), r"\1\)\)"),
    # close missing '\)' before separators
    (re.compile(r"(\\\([^)]*?)(?=\s*(?:=|:|is)\b)", re.IGNORECASE), r"\1\)"),
    # before next item dash "- (", "- \(" or end of line
    (re.compile(r"(\\\([^)]*?_\{[^}]*)(?=\s*-\s*(?:\(|\\\(|$))", re.IGNORECASE), r"\1\)\)"),
    (re.compile(r"(\\\([^)]*?)(?=\s*-\s*(?:\(|\\\(|$))", re.IGNORECASE), r"\1\)"),
]

def _heal_unclosed_inline_in_where(line: str) -> str:
    """Repair unclosed \( ... and missing '}' inside where: lines."""
    if "where:" not in line.lower():
        return line
    s = line
    # collapse multi-backslashes first
    s = re.sub(r"\\{2,}\(", r"\\(", s)
    s = re.sub(r"\\{2,}\)", r"\\)", s)
    for rx, repl in _HEAL_UNCLOSED_INLINE_BEFORE_SEP:
        s = rx.sub(repl, s)
    # If we introduced '))' in the {..}}) case, reduce to '}\\)'
    s = re.sub(r"\}\)\)", r"}\\)", s)
    return s

def _expand_where_runon(line: str) -> str:
    """
    Split 'where: - (\sigma) = desc - (\mu) is desc - (n) = desc'
    (or with \( \sigma \)) into bullets. Tokens are rewrapped using _inline().
    """
    i = line.lower().find("where:")
    if i == -1:
        return line
    prefix = line[: i + len("where:")].strip()
    rest   = line[i + len("where:"):].strip()

    # Heal any unclosed inline maths in the "rest" portion (again, local to this line)
    rest = _heal_unclosed_inline_in_where(rest)

    items = []
    pos = 0
    m = INLINE_ITEM_RE.search(rest, pos)
    if not m:
        return line

    while m:
        tok = (m.group(1) or m.group(2)).strip()
        start = m.end()
        next_m = INLINE_ITEM_RE.search(rest, start)
        desc = rest[start: next_m.start()].strip() if next_m else rest[start:].strip()
        desc = re.sub(r"^[\s:=\-–—]+", "", desc)
        items.append((tok, desc))
        if not next_m:
            break
        m = next_m

    out = [prefix] + [f"- {_inline(tok)}: {desc}" for tok, desc in items]
    return "\n".join(out)

# ---------- main API ----------
def sanitize_katex(text: str) -> str:
    """
    - Pre-normalise: collapse multi-backslashes around \( \); heal unclosed inline math in 'where:' lines
    - Split 'where:' run-on BEFORE protecting math (after healing)
    - Protect math; in non-math text:
        * wrap (\sigma) etc. as \(\sigma\)
        * split 'where:' run-on AGAIN (catches newly wrapped items)
        * normalise (0-10) -> (0{-}10)
    - Restore math; escape % inside $$...$$; ensure blank line after display blocks
    - Remove spaces inside \(...\)
    """
    if not text:
        return text

    parts = CODE_FENCE_RE.split(text)  # don't touch ```...``` blocks

    def fix(seg: str) -> str:
        # (0) punctuation normalisation
        seg = (seg.replace("–", "-").replace("—", "-")
                 .replace("“", '"').replace("”", '"').replace("’", "'"))

        # (0.a) collapse ANY run of backslashes before \( or \)
        seg = re.sub(r"\\{2,}\(", r"\\(", seg)
        seg = re.sub(r"\\{2,}\)", r"\\)", seg)

        # (0.b) heal unclosed inline math in 'where:' lines (so the splitter can see items)
        seg = "\n".join(_heal_unclosed_inline_in_where(line) for line in seg.splitlines())

        # (0.c) split 'where:' run-on now (works with raw and inline forms)
        seg = "\n".join(_expand_where_runon(line) for line in seg.splitlines())

        # --- protect existing math spans ---
        seg, dlist, ilist = _protect_math(seg)

        # (1) rare brace glitch in plain text
        seg = re.sub(r"\}\}\)", "})", seg)

        # (2) (\sigma) -> \(\sigma\) (wrap NEW bare tokens)
        seg = PARENS_MATH_RE.sub(lambda m: _inline(m.group(1)), seg)

        # (3) split 'where:' again (in case wrapping created inline items)
        seg = "\n".join(_expand_where_runon(line) for line in seg.splitlines())

        # (4) normalise ranges outside math: (0-10) -> (0{-}10)
        seg = re.sub(r"\((\s*\d+)\s*-\s*(\d+\s*)\)", r"(\1{-}\2)", seg)

        # --- restore math ---
        seg = _restore_math(seg, dlist, ilist)

        # (5) escape % inside display math
        seg = DISPLAYMATH_RE.sub(lambda m: _escape_percent_in_display(m.group(0)), seg)

        # (6) blank line after $$...$$ if content follows
        seg = re.sub(r"(\$\$[\s\S]*?\$\$)(?=\S)", r"\1\n\n", seg)

        # (7) remove spaces inside inline delimiters anywhere
        seg = re.sub(r"\\\(\s+", r"\\(", seg)
        seg = re.sub(r"\s+\\\)", r"\\)", seg)

        return seg

    for i in range(len(parts)):
        if not parts[i].startswith("```"):
            parts[i] = fix(parts[i])

    return "".join(parts)
