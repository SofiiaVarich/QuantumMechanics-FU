import asyncio
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest
from aiohttp.test_utils import TestClient, TestServer

from quantum_tutor.config import Settings
from quantum_tutor.web.server import STATIC, create_web_app, latex_for_choice
from test_web_auth import TOKEN, signed_data


ROOT = Path(__file__).resolve().parents[1]


def test_choice_latex_preserves_literal_text():
    assert latex_for_choice("E = hν") == r"\text{E = hν}"
    assert latex_for_choice("ψ(x) = A; E ≠ 0") == r"\text{ψ(x) = A; E ≠ 0}"
    assert latex_for_choice(r"\frac{x_1}{y^2} & 50% #$~") == (
        r"\text{\textbackslash{}frac\{x\_1\}\{y\textasciicircum{}2\}"
        r" \& 50\% \#\$\textasciitilde{}}"
    )


def test_formula_api_uses_exact_choice_text_and_retains_feedback_metadata(tmp_path):
    settings = Settings(TOKEN, tmp_path / "db.sqlite", ROOT / "curriculum", (123,), "Europe/Berlin", "20:00")
    catalog = {}
    for path in (ROOT / "curriculum").glob("topic_*.json"):
        catalog.update(json.loads(path.read_text()).get("concept_metadata", {}))

    async def scenario():
        headers = {"Authorization": "tma " + signed_data(123, int(time.time()))}
        async with TestClient(TestServer(create_web_app(settings))) as client:
            for topic in range(1, 21):
                response = await client.post("/api/session", headers=headers, json={"mode": "formula", "topic_id": topic})
                assert response.status == 200
                state = await response.json()
                if state["complete"]:
                    continue
                question = state["question"]
                for choice in question["choices"]:
                    assert choice["latex"] == latex_for_choice(choice["text"])
                response = await client.post("/api/answer", headers=headers, json={"question_id": question["id"], "choice_index": None})
                assert response.status == 200
                feedback = (await response.json())["feedback"]
                assert feedback["latex"] == catalog.get(question["card_id"], {}).get("formula_latex", "")

    asyncio.run(scenario())


def run_node(script, *args):
    if not shutil.which("node"):
        pytest.skip("Node.js is needed for JavaScript rendering tests")
    subprocess.run(["node", "-e", script, *map(str, args)], check=True, timeout=30)


def test_math_rendering_falls_back_safely():
    run_node(r"""
const assert = require('node:assert/strict');
const fs = require('node:fs');
const source = fs.readFileSync(process.argv[1], 'utf8');
const math = new Function('window', source.slice(source.indexOf('  function math('), source.indexOf('  function navigation(')) + '; return math;');
const container = { textContent: '' };
let calls = 0;
const render = math({ katex: { render(latex, target, options) {
  calls++;
  assert.equal(options.throwOnError, true);
  assert.equal(options.trust, false);
  target.textContent = 'partial render';
  throw new Error('invalid formula');
} } });
render(container, '\\invalid', '<img src=x onerror=alert(1)>');
assert.equal(calls, 1);
assert.equal(container.textContent, '<img src=x onerror=alert(1)>');
math({})(container, 'metadata', 'readable answer');
assert.equal(container.textContent, 'readable answer');
math({ katex: { render(_, target) { target.textContent = 'rendered'; } } })(container, 'x', 'fallback');
assert.equal(container.textContent, 'rendered');
assert.ok(source.includes('math(formula, feedback.latex, feedback.answer)'));
""", STATIC / "app.js")


def test_catalog_latex_parses_with_katex(tmp_path):
    """Opt in with KATEX_JS pointing to the page's KaTeX 0.16.11 JS bundle."""
    bundle = os.environ.get("KATEX_JS")
    if not bundle:
        pytest.skip("Set KATEX_JS to validate catalog formulas using real KaTeX")
    formulas = []
    for path in sorted((ROOT / "curriculum").glob("topic_*.json")):
        data = json.loads(path.read_text())
        for card_id, metadata in data.get("concept_metadata", {}).items():
            if metadata.get("formula_latex"):
                formulas.append([card_id, metadata["formula_latex"]])
    formulas.extend([['literal choice', latex_for_choice("ψ(x) = A_0; {x} = 50% & #$~^\\")]])
    payload = tmp_path / "formulas.json"
    payload.write_text(json.dumps(formulas))
    run_node(r"""
const assert = require('node:assert/strict');
const katex = require(process.argv[1]);
assert.equal(katex.version, '0.16.11');
const formulas = JSON.parse(require('node:fs').readFileSync(process.argv[2], 'utf8'));
assert.ok(formulas.length > 1);
const failures = [];
for (const [id, latex] of formulas) {
  try { katex.renderToString(latex, { throwOnError: true, trust: false, strict: 'ignore' }); }
  catch (error) { failures.push(`${id}: ${error.message}`); }
}
assert.deepEqual(failures, []);
console.log(`Parsed ${formulas.length} catalog/literal formulas with KaTeX ${katex.version}`);
""", Path(bundle).resolve(), payload)
