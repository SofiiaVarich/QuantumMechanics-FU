"""Execute graphics lifecycle paths with deterministic DOM/Three doubles, not a GPU."""
import shutil
import subprocess
from pathlib import Path

import pytest

STATIC = Path(__file__).resolve().parents[1] / 'src/quantum_tutor/web/static'

HARNESS = r"""
const assert = require('node:assert/strict');
class Target {
  constructor() { this.listeners = new Map(); this.classList = {add(){},remove(){}}; this.dataset = {}; }
  addEventListener(t, f) { this.listeners.set(t, f); }
  removeEventListener(t, f) { if(this.listeners.get(t) === f) this.listeners.delete(t); }
  emit(t, e = {}) { this.listeners.get(t)?.(e); }
  setPointerCapture() {}
    getBoundingClientRect(){return {left:0,top:0,width:250,height:250};}
}
let clock = 0, serial = 0, renders = 0, releases = 0, losses = 0, audioDisposals = 0;
const frames = new Map();
const performance = {now: () => clock};
const requestAnimationFrame = f => {frames.set(++serial, f); return serial;};
const cancelAnimationFrame = id => frames.delete(id);
const document = new Target(); document.hidden = false;
document.currentScript = {src:'https://example.test/crystal.js'};
document.createElement = () => new Target();
const window = new Target(); window.location = {href:'https://example.test/'};
window.createCrystalAudio = () => ({dispose(){audioDisposals++;},end(){},update(){}});
window.AtlasInertia = {step: () => ({delta:0,velocity:0}),release: () => ({x:0,y:0})};
const devicePixelRatio = 1;
class Vec {
  constructor(){this.x=0;this.y=0;this.z=1;}
  normalize(){return this;} fromArray(){return this;} toArray(){return this;}
  multiplyScalar(){return this;} set(){return this;} copy(){return this;} lerp(){return this;}
}
const renderers = [], geometries = [], materials = [];
class Renderer {
  constructor({canvas}) {this.domElement=canvas; renderers.push(this);}
  setPixelRatio(){} setSize(){} setClearColor(){} setScissorTest(){} clear(){} setViewport(){} setScissor(){}
  render(){renders++;} dispose(){releases++;}
  forceContextLoss(){losses++; this.domElement.emit('webglcontextlost');}
}
class Geometry {
  constructor(){this.attributes={position:{array:new Float32Array(9),count:3}};this.disposals=0;geometries.push(this);}
  dispose(){this.disposals++;}
}
class Material {constructor(){this.disposals=0;materials.push(this);} dispose(){this.disposals++;}}
window.THREE = {
  WebGLRenderer:Renderer, Vector3:Vec, Color:Vec, IcosahedronGeometry:Geometry, SphereGeometry:Geometry,
  ShaderMaterial:Material, Scene:class {add(){}},
  PerspectiveCamera:class {constructor(){this.position={};} updateMatrixWorld(){}},
  Mesh:class {constructor(g,m){this.material=m;this.rotation={set(){},x:0,y:0};} updateMatrixWorld(){}},
  Raycaster:class {constructor(){this.ray={intersectSphere:()=>false};} setFromCamera(){}}, Sphere:class {}
};
"""


def run_graphics(filename, checks):
    if not shutil.which('node'):
        pytest.skip('Node is required')
    result = subprocess.run(
        ['node', '-e', HARNESS + (STATIC / filename).read_text() + checks],
        capture_output=True, text=True, timeout=20,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_crystal_coalesces_frames_and_tears_down_once():
    run_graphics('crystal.js', r"""
const element = new Target(), canvas = new Target(), reduced = new Target(); reduced.matches=false;
const crystal = window.createAtlasCrystal(element, canvas, reduced, () => 'all');
assert.equal(renders,1);
for(let i=0;i<100;i++) element.emit('pointerup');
// Hover changes still request a redraw, but never render inside the input handler.
for(let i=0;i<100;i++) element.emit('pointermove',{clientX:0,clientY:0});
assert.equal(renders,1); assert.equal(frames.size,1);
clock=16; crystal.draw();
assert.equal(renders,2); assert.equal(frames.size,0,'atlas frame consumes pending input redraw');
element.emit('pointermove',{}); assert.equal(frames.size,1);
document.hidden=true; document.emit('visibilitychange'); assert.equal(frames.size,0);
crystal.draw(); assert.equal(renders,2);
document.hidden=false; element.emit('pointermove',{});
const stale = [...frames.values()][0];
canvas.emit('webglcontextlost');
assert.equal(losses,0,'already lost context must not be forced lost again');
assert.equal(frames.size,0); stale(); crystal.draw(); crystal.dispose();
assert.equal(renders,2); assert.equal(releases,1); assert.equal(audioDisposals,1);
assert.ok(geometries.every(g=>g.disposals===1)); assert.ok(materials.every(m=>m.disposals===1));
assert.equal(element.listeners.size,0);
const next = window.createAtlasCrystal(new Target(), new Target(), reduced, ()=>'all');
next.dispose(); next.dispose(); assert.equal(losses,1); assert.equal(releases,2);
""")


def test_minis_skip_hidden_tiles_and_survive_stale_calls():
    run_graphics('mini-crystals.js', r"""
let copies=0;
const spheres = [false,true].map(hidden=>{
 const sphere=new Target(); sphere.hidden=hidden;
 sphere.querySelector=()=>({getContext:()=>({clearRect(){},drawImage(){copies++;}})});
 return sphere;
});
const minis=window.createAtlasMiniCrystals(spheres);
minis.draw(0); assert.equal(renders,1); assert.equal(copies,1);
minis.draw(10); assert.equal(renders,1);
document.hidden=true; minis.draw(100); assert.equal(renders,1);
document.hidden=false; spheres[1].hidden=false; minis.draw(100); assert.equal(renders,3);
renderers[0].domElement.emit('webglcontextlost');
minis.dispose(); minis.draw(200);
assert.equal(renders,3); assert.equal(releases,1); assert.equal(losses,0);
assert.ok(geometries.every(g=>g.disposals===1)); assert.ok(materials.every(m=>m.disposals===1));
const next=window.createAtlasMiniCrystals(spheres); next.dispose(); next.dispose();
assert.equal(releases,2); assert.equal(losses,1);
""")
