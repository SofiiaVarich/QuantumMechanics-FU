"""Execute the real UI request/lifecycle code with deterministic timers and fetches."""
import shutil
import subprocess
from pathlib import Path

import pytest


APP = Path(__file__).resolve().parents[1] / "src/quantum_tutor/web/static/app.js"


@pytest.mark.parametrize("scenario", ["timeout", "body_timeout", "network", "http", "answer", "stale", "stale_answer", "stale_reload", "stale_end", "end", "reload"])
def test_ui_recovery(scenario):
    if not shutil.which("node"):
        pytest.skip("Node.js is required for UI execution tests")
    harness = r"""
const fs = require('fs');
const vm = require('vm');
const assert = require('assert/strict');
const scenario = process.argv[2];
let timeout, aborted = false, pending, requestCount = 0;
const controls = [{disabled: false}, {disabled: false}];
const choices = {querySelectorAll: () => [controls[0]]};
const app = {
  setAttribute(name, value) { this[name] = value; },
  querySelectorAll(selector) { return selector === '.choices button' ? [controls[0]] : controls; },
  querySelector() { return null; }
};
const context = {
  document: {getElementById: id => id === 'app' ? app : {}},
  window: {Telegram: {WebApp: {initData: 'test'}}},
  AbortController, console,
  setTimeout(callback) { timeout = callback; return 1; },
  clearTimeout() { timeout = null; },
  fetch: async (path, options) => {
    requestCount++;
    options.signal.addEventListener('abort', () => { aborted = true; });
    if (scenario === 'network') throw new Error('offline');
    if (scenario === 'http') return {ok: false, status: 503};
    if (scenario === 'body_timeout') return {ok: true, json: () => new Promise(() => {})};
    return new Promise(resolve => { pending = resolve; });
  }
};
let source = fs.readFileSync(process.argv[1], 'utf8');
source = source.slice(0, source.indexOf("  document.getElementById('brand')")) + `
  let errors = [], renders = 0;
  showError = (error, retry, label) => { errors.push({error, retry, label}); };
  showSession = () => { renders++; };
  home = () => { renders++; };
  session = {question: {id: 'q1'}};
  globalThis.ui = {api, start, submit, reloadSession, endSession,
    state: () => ({busy, session, uncertainAnswer, errors, renders}),
    navigate: () => { screenVersion++; },
    choices: null};
})();`;
vm.runInNewContext(source, context);
const ui = context.ui;
const flush = async () => { for (let i = 0; i < 12; i++) await Promise.resolve(); };
(async () => {
  if (['timeout', 'body_timeout', 'network', 'http'].includes(scenario)) {
    const operation = ui.start(1, false);
    await flush();
    if (timeout) timeout();
    await operation;
    assert.equal(ui.state().busy, false);
    assert.ok(controls.every(control => !control.disabled));
    assert.equal(app['aria-busy'], 'false');
    assert.equal(ui.state().errors.length, 1);
    assert.equal(ui.state().errors[0].retry, ui.reloadSession);
    if (scenario.includes('timeout')) assert.equal(aborted, true);
  } else if (scenario === 'answer') {
    const operation = ui.submit('q1', 0, choices);
    await flush(); timeout(); await operation;
    assert.equal(ui.state().busy, false);
    assert.equal(controls[0].disabled, true);
    assert.equal(controls[1].disabled, false);
    await ui.submit('q1', 0, choices);
    assert.equal(requestCount, 1);
    assert.equal(ui.state().errors[0].label, 'Resume session');
    const recovery = ui.reloadSession();
    await flush();
    pending({ok: true, json: async () => ({question: {id: 'q2'}})});
    await recovery;
    assert.equal(ui.state().uncertainAnswer, null);
    assert.equal(ui.state().session.question.id, 'q2');
    assert.equal(ui.state().renders, 1);
  } else if (scenario.startsWith('stale')) {
    const operation = scenario === 'stale_answer' ? ui.submit('q1', 0, choices)
      : scenario === 'stale_reload' ? ui.reloadSession()
      : scenario === 'stale_end' ? ui.endSession() : ui.start(1, false);
    await flush(); ui.navigate();
    pending({ok: true, json: async () => ({question: {id: 'stale'}})});
    await operation;
    assert.equal(ui.state().session.question.id, 'q1');
    assert.equal(ui.state().renders, 0);
    assert.equal(ui.state().busy, false);
  } else {
    const operation = scenario === 'end' ? ui.endSession() : ui.reloadSession();
    await flush(); timeout(); await operation;
    assert.equal(ui.state().busy, false);
    assert.ok(controls.every(control => !control.disabled));
    assert.equal(ui.state().session.question.id, 'q1');
    assert.equal(ui.state().errors[0].retry, ui.reloadSession);
  }
  assert.equal(timeout, null);
})().catch(error => { console.error(error); process.exitCode = 1; });
"""
    subprocess.run(
        ["node", "-e", harness, str(APP), scenario],
        check=True, capture_output=True, text=True, timeout=10,
    )
