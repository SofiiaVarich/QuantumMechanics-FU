"""Browser regression checks; optional Playwright, no Telegram credentials or backend."""
import copy
import os
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

STATIC = Path(__file__).resolve().parents[1] / "src/quantum_tutor/web/static"


@pytest.fixture(scope="module")
def browser():
    playwright = pytest.importorskip("playwright.sync_api")
    with playwright.sync_playwright() as runner:
        try:
            instance = runner.chromium.launch(channel="chromium", headless=True)
        except playwright.Error as error:
            pytest.skip(f"Install Playwright Chromium to run layout checks: {error}")
        yield instance
        instance.close()


@pytest.fixture(scope="module")
def static_url():
    class QuietHandler(SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(STATIC)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)


def inside(page, selector):
    return page.locator(selector).evaluate("el => { const r = el.getBoundingClientRect(); return r.top >= 0 && r.bottom <= innerHeight + 1 && r.left >= 0 && r.right <= innerWidth + 1; }")


@pytest.mark.parametrize("width,height", [(320, 568), (375, 667), (390, 844), (430, 932)])
def test_exercise_viewport(browser, static_url, width, height):
    page = browser.new_page(viewport={"width": width, "height": height})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.add_init_script("""
      window.testEvents = {};
      window.Telegram = {WebApp: {initData: 'frontend-test-only', ready() {}, expand() {},
        onEvent(name, fn) { (testEvents[name] ||= new Set()).add(fn); },
        offEvent(name, fn) { testEvents[name]?.delete(fn); },
        BackButton: {show() {}, hide() {}, onClick() {}}}};
    """)
    state = {"title": "Quantum dynamics and the time evolution of physical states " * 4,
             "complete": False, "completed": 0, "total": 4, "percent": 0, "position": 1,
             "question": {"id": "q1", "prompt": "Which equation describes the energy?",
                          "choices": [{"text": f"E = {i} hν", "latex": f"E = {i} h\\nu"} for i in range(1, 5)]}}
    submitted = []

    def api(route):
        path = route.request.url.split("/api/")[1]
        if path.startswith("topics"):
            data = {"topics": [{"number": 1, "title": "Dynamics", "card_count": 4, "percent": 0}], "review_count": 0}
        elif path == "answer":
            submitted.append(route.request.post_data_json)
            data = {"state": state, "feedback": {"correct": True, "answer": "Explanation. " * 120,
                                                    "latex": "E = h\\nu", "source_note": "Test source"}}
        else:
            data = state
        route.fulfill(json=data)

    page.route("**/api/**", api)
    # Real KaTeX when its bundle is available locally; no external network needed.
    katex = Path(os.environ.get("KATEX_JS", "/nonexistent-katex-bundle"))
    katex_css = Path(os.environ.get("KATEX_CSS", "/nonexistent-katex-styles"))
    def external(route):
        if "katex.min.js" in route.request.url and katex.exists():
            route.fulfill(path=str(katex), content_type="application/javascript")
        elif "katex.min.css" in route.request.url and katex_css.exists():
            route.fulfill(path=str(katex_css), content_type="text/css")
        else:
            route.abort()
    page.route("https://**/*", external)
    try:
        page.goto(static_url)
        page.locator(".topic-card").click()
        page.wait_for_selector("[data-layout='together']")
        assert page.locator(".choice").count() == 4
        assert inside(page, ".exercise-question")
        assert inside(page, ".unknown")
        for index in range(4):
            assert inside(page, f".choice:nth-child({index + 1})")
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        assert page.locator("footer").is_hidden()
        assert page.locator(".exercise-switcher").is_hidden()
        page.locator(".session-title").click()
        assert page.get_by_role("dialog").is_visible()
        assert page.locator("#session-title-heading").text_content() == state["title"]
        page.keyboard.press("Escape")
        page.locator(".choice").nth(2).click()
        page.wait_for_selector(".feedback")
        assert submitted == [{"question_id": "q1", "choice_index": 2}]
        assert inside(page, ".feedback .wide")
        assert page.locator(".feedback-detail").evaluate("el => el.scrollHeight > el.clientHeight")
        # Next renders a fundamentally oversized question and more than four answers.
        state["question"] = copy.deepcopy(state["question"])
        state["question"]["prompt"] = "A complete long question with no omitted information. " * 70
        state["question"]["choices"] *= 2
        state["question"]["choices"][0] = {"text": "E = " + "hν + " * 80, "latex": "E = " + r"\frac{h\nu}{2} + " * 80 + "0"}
        # State was already returned with the preceding answer; serve the larger next state.
        page.reload()
        page.locator(".topic-card").click()
        page.wait_for_selector("[data-layout='focus']")
        assert page.locator(".exercise-question").is_visible()
        assert page.locator(".exercise-question").evaluate("el => el.scrollHeight > el.clientHeight")
        assert page.locator(".choice").count() == 8
        page.get_by_role("button", name="Answers", exact=True).click()
        assert page.locator(".exercise-question").is_hidden()
        assert inside(page, ".choices")
        assert page.locator(".math").first.evaluate("el => el.scrollWidth > el.clientWidth")
        page.locator(".choice").first.focus()
        page.keyboard.press("ArrowRight")
        assert page.locator(".math").first.evaluate("el => el.scrollLeft > 0")
        page.locator(".unknown").scroll_into_view_if_needed()
        page.locator(".unknown").click()
        page.wait_for_selector(".feedback")
        assert submitted[-1]["choice_index"] is None
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        page.locator(".feedback .wide").click()
        page.wait_for_selector("[data-layout='focus']")
        page.evaluate("document.documentElement.style.setProperty('--tg-viewport-stable-height', '480px'); testEvents.viewportChanged.forEach(fn => fn({isStateStable:true}))")
        page.wait_for_timeout(100)
        assert page.locator(".app-shell").evaluate("el => el.getBoundingClientRect().height") == 480
        assert page.evaluate("testEvents.viewportChanged.size") == 1
        page.get_by_role("button", name="End session", exact=True).click()
        page.wait_for_selector(".topic-card")
        assert page.evaluate("testEvents.viewportChanged.size") == 0
        assert page.locator("footer").is_visible()
        assert not errors
    finally:
        page.close()
