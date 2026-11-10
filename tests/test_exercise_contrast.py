"""WCAG contrast regression checks, with optional real-browser cascade coverage."""
import re
from pathlib import Path

import pytest

from test_exercise_layout import browser  # Reuse the optional Playwright fixture.

CSS = (Path(__file__).resolve().parents[1] / "src/quantum_tutor/web/static/styles.css").read_text()


def rgb(value):
    if value.startswith("#"):
        assert len(value) == 7, f"Session colors must be opaque: {value}"
        return tuple(int(value[i:i + 2], 16) / 255 for i in (1, 3, 5))
    numbers = [float(n) for n in re.findall(r"[\d.]+", value)]
    assert len(numbers) == 3 or numbers[3] == 1, value
    return tuple(n / 255 for n in numbers[:3])


def contrast(first, second):
    def luminance(color):
        channels = [c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4 for c in rgb(color)]
        return sum(c * weight for c, weight in zip(channels, (.2126, .7152, .0722)))
    a, b = sorted((luminance(first), luminance(second)))
    return (b + .05) / (a + .05)


def palette(theme):
    selector = ".exercise-session .app-shell" if theme == "light" else ":root[data-theme='dark'] .exercise-session .app-shell"
    blocks = re.findall(r"(?:^|\n)" + re.escape(selector) + r"\s*\{([^}]+)\}", CSS)
    assert blocks
    return dict(re.findall(r"(--[\w-]+):\s*(#[\da-f]+);", blocks[-1]))


@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize("disabled", [False, True])
@pytest.mark.parametrize("state", ["answer", "hover", "active"])
def test_session_palette_contrast(theme, disabled, state):
    colors = palette(theme)
    background = colors["--session-answer" if disabled else "--session-" + state]
    # Text, formulas, and letter badges use the same full-opacity foreground.
    for surface in (background, colors["--session-answer"]):
        assert contrast(colors["--text"], surface) >= 7
        assert contrast(colors["--border"], surface) >= 3
    assert contrast(colors["--border"], colors["--surface"]) >= 3
    assert contrast(colors["--session-accent"], background) >= 3
    for kind in ("green", "red"):
        assert contrast(colors["--" + kind], colors["--" + kind + "-soft"]) >= 7
        assert contrast(colors["--text"], colors["--" + kind + "-soft"]) >= 7
        assert contrast(colors["--" + kind], colors["--surface"]) >= 3


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_computed_answer_contrast(browser, theme):
    page = browser.new_page()
    try:
        page.set_content(f"""<html data-theme='{theme}'><body class='exercise-session'>
          <div class='app-shell'><div class='question-panel'>
          <button class='choice'><span class='choice-letter'>A</span>
          <span class='choice-content'>Energy<span class='math'><span class='katex'>E = hν</span></span></span></button>
          <button class='text-button unknown'>I don't know</button>
          <div class='feedback correct'><h2>Correct</h2><span class='math'><span class='katex'>E = hν</span></span></div>
          <div class='feedback incorrect'><h2>Incorrect</h2><span class='math'><span class='katex'>E = hν</span></span></div>
          </div></div></body></html>""")
        page.add_style_tag(content=CSS)
        def style(selector):
            return page.locator(selector).evaluate("""el => {
              const s = getComputedStyle(el);
              return {color: s.color, background: s.backgroundColor, border: s.borderTopColor,
                opacity: s.opacity, fill: s.webkitTextFillColor, outline: s.outlineColor};
            }""")
        panel = style('.question-panel')
        for disabled in (False, True):
            for selector in ('.choice', '.unknown'):
                button = page.locator(selector)
                button.evaluate('(el, disabled) => el.disabled = disabled', disabled)
                for state in ('normal', 'focus', 'hover', 'active'):
                    page.mouse.move(0, 0)
                    button.evaluate('el => el.blur()')
                    if state == 'focus' and not disabled:
                        button.focus()
                    if state in ('hover', 'active'):
                        button.hover()
                    if state == 'active':
                        page.mouse.down()
                    try:
                        answer = style(selector)
                        assert answer['opacity'] == '1'
                        assert answer['fill'] == answer['color']
                        assert contrast(answer['color'], answer['background']) >= 7
                        assert contrast(answer['border'], answer['background']) >= 3
                        assert contrast(answer['border'], panel['background']) >= 3
                        if state == 'focus' and not disabled:
                            assert contrast(answer['outline'], panel['background']) >= 3
                        if selector == '.choice':
                            letter = style('.choice-letter')
                            assert contrast(letter['color'], letter['background']) >= 7
                            assert contrast(letter['border'], answer['background']) >= 3
                            formula = style('.choice .katex')
                            assert formula['color'] == answer['color'] == formula['fill']
                    finally:
                        if state == 'active':
                            page.mouse.up()
        for kind in ('correct', 'incorrect'):
            feedback = style('.feedback.' + kind)
            heading = style('.feedback.' + kind + ' h2')
            formula = style('.feedback.' + kind + ' .katex')
            assert contrast(heading['color'], feedback['background']) >= 7
            assert contrast(formula['color'], feedback['background']) >= 7
            assert contrast(feedback['border'], panel['background']) >= 3
        page.emulate_media(forced_colors='active')
        assert page.locator('.choice').evaluate('el => getComputedStyle(el).forcedColorAdjust') == 'auto'
    finally:
        page.close()
