"""Literal presentation conversion, deliberately not a physics/symbolic simplifier.

Unpaired catalog metadata is never an answer renderer. Unsupported notation stays
readable text; callers must retain that fallback even when LaTeX is available.
"""
from __future__ import annotations

import re

GREEK = dict(zip(
    "αβγδεζηθικλμνξοπρστυφχψωΓΔΘΛΞΠΣΦΨΩ",
    "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu nu xi omicron pi rho sigma tau upsilon phi chi psi omega Gamma Delta Theta Lambda Xi Pi Sigma Phi Psi Omega".split(),
))
SYMBOLS = {
    **{key: "\\" + value + " " for key, value in GREEK.items()},
    "ℏ": r"\hbar ", "⟨": r"\langle ", "⟩": r"\rangle ",
    "∫": r"\int ", "∮": r"\oint ", "∑": r"\sum ",
    "∂": r"\partial ", "∇": r"\nabla ", "∞": r"\infty ",
    "⊗": r"\otimes ", "⊕": r"\oplus ", "·": r"\cdot ",
    "×": r"\times ", "−": "-", "–": "-", "≥": r"\ge ",
    "≤": r"\le ", "≠": r"\ne ", "≈": r"\approx ", "∝": r"\propto ",
    "∈": r"\in ", "∉": r"\notin ", "→": r"\to ", "↔": r"\leftrightarrow ",
    "⇒": r"\Rightarrow ", "⇔": r"\Leftrightarrow ", "±": r"\pm ",
    "†": r"^{\dagger}", "′": "'", "″": "''", "…": r"\ldots ",
    "ℂ": r"\mathbb{C}", "ℝ": r"\mathbb{R}", "ℕ": r"\mathbb{N}",
    "½": r"\frac{1}{2}", "¼": r"\frac{1}{4}",
    "{": r"\{", "}": r"\}", "%": r"\%", "&": r"\&", "#": r"\#", "$": r"\$",
}
SUP = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻ⁿ", "0123456789+-n")
SUB = str.maketrans("₀₁₂₃₄₅₆₇₈₉₊₋ᵢⱼₙₐ", "0123456789+-ijna")


def literal_latex(text: str) -> str:
    """Return structural LaTeX or empty string when literal parsing is uncertain.

    A slash becomes a fraction only with explicit grouped/single-atom operands.
    Implicit products are not regrouped: a/bc remains a/bc, not a/(bc).
    """
    if not text or "\\" in text:
        return ""
    tokens: list[str] = []
    position = 0

    def group(start: int, closing: str) -> tuple[str, int]:
        depth = 1
        opening = text[start]
        end = start + 1
        while end < len(text):
            if text[end] == opening:
                depth += 1
            elif text[end] == closing:
                depth -= 1
                if depth == 0:
                    inside = literal_latex(text[start + 1:end])
                    if not inside and text[start + 1:end]:
                        raise ValueError
                    return inside, end + 1
            end += 1
        raise ValueError

    try:
        while position < len(text):
            char = text[position]
            matrix = re.match(r"\[\[([^\[\]]+)\](?:,\[([^\[\]]+)\])+\]", text[position:])
            if matrix:
                rows = re.findall(r"\[([^\[\]]+)\]", matrix.group())
                cells = [[literal_latex(cell.strip()) for cell in row.split(",")] for row in rows]
                if not cells[0] or any(len(row) != len(cells[0]) or not all(row) for row in cells):
                    return ""
                tokens.append(r"\begin{pmatrix}" + r"\\".join("&".join(row) for row in cells) + r"\end{pmatrix}")
                position += len(matrix.group())
                continue
            if char in "([":
                inside, position = group(position, ")" if char == "(" else "]")
                tokens.append(char + inside + (")" if char == "(" else "]"))
                continue
            if char in ")]":
                return ""
            if char == "√":
                position += 1
                if position == len(text):
                    return ""
                if text[position] in "([":
                    value, position = group(position, ")" if text[position] == "(" else "]")
                else:
                    value = literal_latex(text[position])
                    position += 1
                if not value:
                    return ""
                tokens.append(r"\sqrt{" + value + "}")
                continue
            if ord(char) in SUP or ord(char) in SUB:
                table = SUP if ord(char) in SUP else SUB
                end = position + 1
                while end < len(text) and ord(text[end]) in table:
                    end += 1
                value = text[position:end].translate(table)
                if table is SUP and end + 1 < len(text) and text[end] == "/" and ord(text[end + 1]) in SUP:
                    denominator_end = end + 2
                    while denominator_end < len(text) and ord(text[denominator_end]) in SUP:
                        denominator_end += 1
                    value = r"\frac{" + value + "}{" + text[end + 1:denominator_end].translate(SUP) + "}"
                    end = denominator_end
                if not tokens or tokens[-1].endswith("}") and tokens[-1].startswith(("^", "_")) and tokens[-1][0] == ("^" if table is SUP else "_"):
                    return ""
                tokens.append(("^" if table is SUP else "_") + "{" + value + "}")
                position = end
                continue
            if char in "^_":
                position += 1
                if position == len(text):
                    return ""
                if text[position] in "([":
                    value, position = group(position, ")" if text[position] == "(" else "]")
                else:
                    match = re.match(r"[A-Za-z0-9]+", text[position:])
                    raw = match.group() if match else text[position]
                    value = literal_latex(raw)
                    position += len(raw)
                if not value:
                    return ""
                tokens.append(char + "{" + value + "}")
                continue
            match = re.match(r"[A-Za-z]{3,}", text[position:])
            if match:
                word = match.group()
                tokens.append("\\" + word + " " if word in {"sin", "cos", "tan", "exp", "log", "ln", "det", "lim"} else r"\text{" + word + "}")
                position += len(word)
                continue
            if char in SYMBOLS:
                tokens.append(SYMBOLS[char])
            elif char.isascii() and (char.isalnum() or char in " +-=/|,;:.!<>*'~\n"):
                tokens.append(" " if char == "\n" else char)
            elif char.isalpha():
                # Non-math prose (e.g. German) is safe inside a text segment.
                if char in "äöüÄÖÜß":
                    tokens.append(r"\text{" + char + "}")
                else:
                    return ""
            else:
                return ""
            position += 1
    except ValueError:
        return ""
    result = "".join(tokens)
    # Single atoms or explicitly parenthesized operands only. Never infer a
    # denominator from adjacent implicit multiplication or change slash scope.
    atom = r"(?:\\[A-Za-z]+\s*|[A-Za-z0-9])"
    result = re.sub(r"(?<![A-Za-z0-9}])(" + atom + r")\s*/\s*(" + atom + r")(?![A-Za-z0-9_{^])", r"\\frac{\1}{\2}", result)
    return result


def answer_latex(text: str, card=None) -> str:
    if card is not None and card.formula_answer == text and card.formula_answer_latex:
        return card.formula_answer_latex
    return literal_latex(text)


def blocks(text: str) -> list[dict[str, str]]:
    """Line blocks retain exact text, including prose and source warnings."""
    result = []
    for line in text.splitlines(keepends=True):
        latex = literal_latex(line) if any(c in line for c in "=≥≤≈∝≠∫⟨Σ∑") else ""
        result.append({"type": "math" if latex else "text", "text": line, "latex": latex})
    return result


def audit_catalog(study) -> dict:
    formulas = [card for card in study.cards() if study.has_formula(card)]
    unsupported = []
    paired = 0
    for card in formulas:
        text = study.formula_text(card)
        paired += bool(card.formula_answer == text and card.formula_answer_latex)
        if not answer_latex(text, card):
            unsupported.append({"card_id": card.id, "text": text})
    return {"total": len(formulas), "paired": paired,
            "literal": len(formulas) - len(unsupported) - paired,
            "unsupported": unsupported}
