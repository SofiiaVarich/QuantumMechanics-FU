"""Exercise the actual atlas renderer in Node without a browser dependency."""
import shutil
import subprocess
from pathlib import Path

import pytest

STATIC = Path(__file__).resolve().parents[1] / "src/quantum_tutor/web/static"


def test_atlas_navigation_and_motion():
    if not shutil.which("node"):
        pytest.skip("Node is required for the mocked DOM navigation test")
    source = (STATIC / "app.js").read_text()
    renderer = source[source.index("  function renderAtlas("):source.index("  async function start(")]
    harness = r"""
const assert = require('node:assert/strict');
class Element {
  constructor(tag, text, className) {
    this.tag = tag; this.textContent = text; this.className = className;
    this.children = []; this.listeners = {}; this.style = {}; this.dataset = {};
    this.clientWidth = 240; this.clientHeight = 820;
  }
  append(...items) { this.children.push(...items); }
  setAttribute(key, value) { this[key] = value; }
  addEventListener(key, fn) { this.listeners[key] = fn; }
  removeEventListener(key) { delete this.listeners[key]; }
  contains(el) { return el === this || this.children.includes(el); }
}
const node = (...args) => new Element(...args);
const button = (text, action, cls) => { const b = node('button', text, cls); b.action = action; return b; };
const app = node('main');
const calls = [];
const start = (...args) => calls.push(args);
const percent = value => Math.max(0, Math.min(100, Number(value) || 0));
const mode = 'formula', modes = { formula: ['Formulas'] };
const document = new Element(); document.hidden = false;
const reduced = new Element(); reduced.matches = false;
const window = new Element(); window.matchMedia = () => reduced;
let disposeAtlas;
let serial = 0;
const frames = new Map();
const requestAnimationFrame = fn => { frames.set(++serial, fn); return serial; };
const cancelAnimationFrame = id => frames.delete(id);
const topics = Array.from({length: 20}, (_, i) => ({number: i + 1, title: `API topic ${i + 1}`, card_count: 12, review_count: 3, percent: 25}));
"""
    checks = r"""
renderAtlas(topics.slice().reverse(), false);
const scene = app.children[0];
const spheres = scene.children.filter(el => el.dataset.topicId);
assert.equal(spheres.length, 20);
for (let i = 0; i < 20; i++) {
  spheres[i].action();
  assert.deepEqual(calls.pop(), [i + 1, false]);
}
assert.equal(spheres[2].children[1].textContent, '03');
assert.equal(spheres[14].children[1].textContent, 'E5');
scene.children[1].action();
assert.equal(calls.length, 0, 'crystal interaction must not start a session');
scene.children[2].children[1].action();
assert.deepEqual(calls.pop(), [null, false]);
assert.equal(frames.size, 1);
const filters = app.children.find(el => el.className === 'atlas-filters');
assert.equal(filters.role, 'group');
for (const [index, category] of [[1, 'theory'], [2, 'experiment'], [0, 'all']]) {
  filters.children[index].action();
  assert.equal(scene.dataset.filter, category);
  assert.equal(filters.children[index]['aria-pressed'], 'true');
  assert.equal(filters.children.filter(el => el['aria-pressed'] === 'true').length, 1);
  for (const sphere of spheres) {
    assert.equal(sphere.hidden, category !== 'all' && sphere.dataset.category !== category);
  }
}
// Each immutable topic remains navigable after animation and filtering.
for (let step = 0; step < 100; step++) {
  const [id, fn] = frames.entries().next().value;
  frames.delete(id); fn(step * 50);
  for (const sphere of spheres) {
    assert.ok(Number.isFinite(parseFloat(sphere.style.left)));
    assert.ok(Number.isFinite(parseFloat(sphere.style.top)));
  }
}
for (let i = 0; i < spheres.length; i++) {
  spheres[i].action(); assert.deepEqual(calls.pop(), [i + 1, false]);
}
scene.listeners.focusin(); assert.equal(frames.size, 0);
scene.listeners.focusout({relatedTarget: spheres[0]}); assert.equal(frames.size, 0);
scene.listeners.focusout({relatedTarget: null}); assert.equal(frames.size, 1);
document.hidden = true; document.listeners.visibilitychange(); assert.equal(frames.size, 0);
document.hidden = false; document.listeners.visibilitychange(); assert.equal(frames.size, 1);
reduced.matches = true; reduced.listeners.change(); assert.equal(frames.size, 0);
reduced.matches = false; reduced.listeners.change(); assert.equal(frames.size, 1);
disposeAtlas(); assert.equal(frames.size, 0);
assert.equal(document.listeners.visibilitychange, undefined);
assert.equal(window.listeners.resize, undefined);
renderAtlas(topics, true);
const reviewScene = app.children.findLast(el => el.className === 'atlas-scene');
reviewScene.children[2].children[1].action(); assert.deepEqual(calls.pop(), [null, true]);
reviewScene.children.find(el => el.dataset.topicId === '15').action();
assert.deepEqual(calls.pop(), [15, true]);
disposeAtlas();
"""
    result = subprocess.run(["node", "-e", harness + renderer + checks], capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stdout + result.stderr


def test_atlas_session_loading_resets_on_success_and_failure():
    if not shutil.which("node"):
        pytest.skip("Node is required for the mocked DOM navigation test")
    source = (STATIC / "app.js").read_text()
    start = source[source.index("  async function start("):source.index("  async function reloadSession(")]
    harness = r"""
const assert = require('node:assert/strict');
let busy = false, session = null, mode = 'law', resolve, reject, shown = 0, errors = 0;
const atlas = {setAttribute(key, value) { this[key] = value; }};
const buttons = [{disabled: false}, {disabled: false}];
const app = {
  setAttribute(key, value) { this[key] = value; },
  querySelector() { return atlas; },
  querySelectorAll() { return buttons; }
};
const api = (path, body) => {
  assert.equal(path, '/session');
  assert.deepEqual(body, {mode: 'law', topic_id: 15, review: true});
  return new Promise((yes, no) => { resolve = yes; reject = no; });
};
const showSession = () => { shown++; };
const showError = () => { errors++; };
"""
    checks = r"""
(async () => {
  for (const fail of [false, true]) {
    const pending = start(15, true);
    assert.equal(busy, true);
    assert.equal(atlas['aria-busy'], 'true');
    assert.equal(app['aria-busy'], 'true');
    assert.ok(buttons.every(b => b.disabled));
    await start(15, true); // Duplicate activation must not issue another request.
    if (fail) reject(new Error('offline')); else resolve({id: 123});
    await pending;
    assert.equal(busy, false);
    assert.equal(atlas['aria-busy'], 'false');
    assert.equal(app['aria-busy'], 'false');
    assert.ok(buttons.every(b => !b.disabled));
  }
  assert.equal(shown, 1);
  assert.equal(errors, 1);
})().catch(error => { console.error(error); process.exitCode = 1; });
"""
    result = subprocess.run(["node", "-e", harness + start + checks], capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stdout + result.stderr


def test_atlas_css_state_palette():
    css = (STATIC / "styles.css").read_text()
    assert "#fff, #bff0f5 50%, #56D9E8" in css
    assert "#fff, #c8f1e3 50%, #73D8B8" in css
    for selector, color in [
        (".atlas-scene", "#C9D8EA"),
        (".atlas-scene[data-filter='theory']", "#56D9E8"),
        (".atlas-scene[data-filter='experiment']", "#73D8B8"),
        (".atlas-scene:has(.atlas-core:hover, .atlas-core:focus-visible, .atlas-sphere:hover, .atlas-sphere:focus-visible)", "#477BFF"),
        (".atlas-scene:has(.atlas-core:active, .atlas-sphere:active)", "#9470E8"),
        (".atlas-scene.atlas-scene[aria-busy='true']", "#343F91"),
    ]:
        assert f"{selector} {{ --crystal-color: {color}; }}" in css
    assert "var(--crystal-color)" in css
    assert ".atlas-sphere[hidden] { display: none; }" in css


def test_live_integration_and_valid_shell():
    source = (STATIC / "app.js").read_text()
    html = (STATIC / "index.html").read_text()
    assert "renderAtlas(data.topics, review)" in source
    assert "disposeAtlas();\n    disposeAtlas = () => {};\n    screen = name" in source
    assert "topic_id: topicId, review" in source
    assert "topic.date" in source and "meter(topic.percent" in source
    assert "Authorization: 'tma ' + tg.initData" in source
    assert "fallback || latex || ''" in source
    assert "three@0.128.0/build/three.min.js" in html
    assert 'src="crystal.js?v=9"' in html
    assert 'href="styles.css?v=9"' in html
    assert 'src="app.js?v=9"' in html
    assert "function home() { return topics(mode); }" in source
    assert 'src="https://telegram.org/js/telegram-web-app.js"' in html
    assert html.count("</footer>") == 1
    assert "<div</body>" not in html


def test_crystal_fallback_without_three():
    if not shutil.which("node"):
        pytest.skip("Node is required")
    source = (STATIC / "crystal.js").read_text()
    harness = """
const assert = require('node:assert/strict');
const window = {};
"""
    checks = """
const element = {classList: {remove() {}}, removeEventListener() {}};
const crystal = window.createAtlasCrystal(element, {removeEventListener() {}}, {matches: true}, () => 'all');
crystal.draw(); crystal.dispose(); crystal.dispose();
assert.equal(typeof crystal.dispose, 'function');
"""
    result = subprocess.run(["node", "-e", harness + source + checks], capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stdout + result.stderr


def test_signed_inertia_and_timestep_independence():
    if not shutil.which("node"):
        pytest.skip("Node is required")
    source = (STATIC / "inertia.js").read_text()
    checks = r"""
const assert = require('node:assert/strict');
const motion = window.AtlasInertia;
for (const sign of [-1, 1]) {
  const samples = [{x:0,y:0,t:0},{x:sign*20,y:sign*10,t:40},{x:sign*50,y:sign*25,t:100}];
  const release = motion.release(samples, 105);
  assert.equal(Math.sign(release.x),sign);
  assert.equal(Math.sign(release.y),sign);
  function integrate(dt) {
    let velocity=release.x, angle=0;
    for(let t=0;t<12-dt/2;t+=dt){
      const next=motion.step(velocity,dt);
      assert.ok(next.velocity===0 || Math.sign(next.velocity)===sign);
      assert.ok(next.delta===0 || Math.sign(next.delta)===sign);
      assert.ok(Math.abs(next.velocity)<=Math.abs(velocity));
      angle+=next.delta;velocity=next.velocity;
    }
    assert.equal(velocity,0,'must eventually stop');
    assert.deepEqual(motion.step(velocity,10),{velocity:0,delta:0});
    return angle;
  }
  assert.ok(Math.abs(integrate(1/30)-integrate(1/144))<1e-10);
  assert.ok(Math.abs(motion.step(release.x,3).velocity)>.004,'coasts for several seconds');
  assert.deepEqual(motion.release(samples,250),{x:0,y:0},'stale release cannot fling');
  assert.deepEqual(motion.release(samples,105,true),{x:0,y:0},'reduced motion cannot coast');
}
assert.deepEqual(motion.release([],0),{x:0,y:0});
assert.deepEqual(motion.release([{x:1,y:1,t:1}],1),{x:0,y:0});
const reversed=[{x:0,y:0,t:0},{x:80,y:0,t:150},{x:60,y:0,t:200},{x:40,y:0,t:240}];
assert.ok(motion.release(reversed,245).x<0,'recent direction wins over old samples');
"""
    result = subprocess.run(["node", "-e", "const window={};\n" + source + checks], capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stdout + result.stderr


def test_motion_lifecycle_and_shared_mini_renderer():
    crystal = (STATIC / "crystal.js").read_text()
    minis = (STATIC / "mini-crystals.js").read_text()
    app = (STATIC / "app.js").read_text()
    assert "core.addEventListener('pointercancel',stop)" in crystal
    assert "core.addEventListener('lostpointercapture'" in crystal
    assert "window.AtlasInertia.release(samples,performance.now(),reduced.matches)" in crystal
    assert "window.AtlasInertia.step(vx,dt)" in crystal
    assert "crystal?.stop();" in app
    assert "minis?.dispose();" in app
    assert minis.count("new THREE.WebGLRenderer") == 1
    assert "rd.setScissor" in minis and "ctx.drawImage" in minis
    assert "g?.dispose()" in minis and "mat?.dispose()" in minis
    assert "webglcontextlost" in minis
    assert "mesh.rotation.y+=(reduce?0:.004)" not in crystal


def test_mini_crystals_without_webgl_and_version9_assets():
    html = (STATIC / "index.html").read_text()
    for asset in ["app.js", "crystal.js", "mini-crystals.js", "inertia.js", "styles.css"]:
        assert f"{asset}?v=9" in html
    assert html.count('src="https://') == 3
    if not shutil.which("node"):
        pytest.skip("Node is required")
    source = (STATIC / "mini-crystals.js").read_text()
    checks = """
const sphere={classList:{remove(){}}};
const minis=window.createAtlasMiniCrystals([sphere]);
minis.draw(0);minis.dispose();minis.dispose();minis.draw(100);
"""
    result = subprocess.run(["node", "-e", "const window={};\n" + source + checks], capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stdout + result.stderr
