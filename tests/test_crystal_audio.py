"""Run the real audio controller against a deterministic Web Audio mock."""
import shutil
import subprocess
from pathlib import Path

import pytest

STATIC = Path(__file__).resolve().parents[1] / "src/quantum_tutor/web/static"


def test_crystal_audio_controller():
    if not shutil.which("node"):
        pytest.skip("Node is required for Web Audio mocks")
    harness = r"""
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const events = () => ({handlers: {}, addEventListener(k,f) { this.handlers[k]=f; }, removeEventListener(k) { delete this.handlers[k]; }});
global.window = events(); window.location = {href:'https://example.test/'};
global.document = Object.assign(events(), {hidden:false, currentScript:{src:'https://example.test/static/crystal-audio.js'}});
global.localStorage = {getItem(){throw Error('blocked');},setItem(){throw Error('blocked');}};
let contexts=0, fetches=0, rejectDecode=false, finishDecode, latestContext;
const sources=[];
const param = () => ({value:0, values:[], setTargetAtTime(v){this.values.push(v);},cancelScheduledValues(){}});
class Context {
 constructor(){ contexts++; latestContext=this; this.currentTime=0; this.destination={}; }
 resume(){return Promise.resolve();}
 close(){this.closed=true;return Promise.resolve();}
 decodeAudioData(){return new Promise((resolve,reject)=>{finishDecode=()=>rejectDecode?reject(Error('bad decode')):resolve({});});}
 createBufferSource(){const s={playbackRate:param(),connect(){},disconnect(){},start(){this.started=true;},stop(){this.stopped=true;}};sources.push(s);return s;}
 createGain(){const n={gain:param(),connect(){},disconnect(){}};this.gain=n;return n;}
 createBiquadFilter(){this.filter={frequency:param(),connect(){},disconnect(){}};return this.filter;}
}
window.AudioContext=Context;
global.fetch=async()=>{fetches++;return {ok:true,arrayBuffer:async()=>new ArrayBuffer(1)};};
vm.runInThisContext(fs.readFileSync(process.argv[1],'utf8'));
const flush=async()=>{for(let i=0;i<12;i++) await Promise.resolve();};
(async()=>{
 const a=window.createCrystalAudio();
 assert.equal(contexts,0); assert.equal(fetches,0);
 a.begin({isTrusted:false}); assert.equal(contexts,0);
 a.begin({isTrusted:true,pressure:.5}); await flush();
 a.end(); finishDecode(); await flush(); assert.equal(sources.length,0,'release during decode must stay silent');
 a.begin({isTrusted:true}); await flush(); assert.equal(sources.length,1);
 const s=sources[0]; assert.ok(s.started);
 a.update({speed:0,pressure:.2}); const slow=s.playbackRate.values.at(-1), quiet=latestContext.gain.gain.values.at(-1), dark=latestContext.filter.frequency.values.at(-1);
 a.update({speed:2000,pressure:1}); assert.ok(s.playbackRate.values.at(-1)>slow);
  assert.ok(latestContext.gain.gain.values.at(-1)>quiet);
  assert.ok(latestContext.gain.gain.values.at(-1)<=.1721);
   assert.ok(latestContext.filter.frequency.values.at(-1)>dark);
   assert.ok(latestContext.filter.frequency.values.at(-1)<=8000);
  
 a.update({speed:Infinity,pressure:NaN}); assert.ok(Number.isFinite(s.playbackRate.values.at(-1)));
 a.setMuted(true); assert.ok(s.stopped);
 a.setMuted(false); assert.equal(sources.length,1,'unmute is not autoplay');
 a.begin({isTrusted:true}); await flush(); assert.equal(fetches,1,'buffer is cached per page');
 document.hidden=true; document.handlers.visibilitychange(); assert.ok(sources.at(-1).stopped);
 document.hidden=false; a.begin({isTrusted:true}); a.dispose(); await flush();
 assert.equal(sources.length,2,'dispose invalidates pending start');
 assert.equal(document.handlers.visibilitychange,undefined);
 // Fresh script scope provides a fresh cache for rejection and retry coverage.
 vm.runInThisContext(fs.readFileSync(process.argv[1],'utf8'));
 const b=window.createCrystalAudio(); rejectDecode=true;
 b.begin({isTrusted:true}); await flush(); finishDecode(); await flush();
 assert.equal(sources.length,2);
 rejectDecode=false; b.begin({isTrusted:true}); await flush(); finishDecode(); await flush();
 assert.equal(sources.length,3,'decode failure is retryable');
 window.handlers.pagehide(); assert.ok(sources.at(-1).stopped); b.dispose();
})().catch(error=>{console.error(error);process.exitCode=1;});
"""
    result = subprocess.run(
        ["node", "-e", harness, str(STATIC / "crystal-audio.js")],
        capture_output=True, text=True, timeout=15,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_audio_asset_is_small_mp3():
    asset = STATIC / "crystal-crumple.mp3"
    assert 1000 < asset.stat().st_size < 100_000
    assert asset.read_bytes()[:3] == b"ID3"


def test_crystal_integration():
    if not shutil.which("node"):
        pytest.skip("Node required")
    # Reuse the deterministic audio graph, but dispatch through the real integration.
    import inspect
    harness = inspect.getsource(test_crystal_audio_controller).split('harness = r"""', 1)[1].split('"""', 1)[0]
    harness = harness[:harness.index("(async()=>{")]
    harness += r"""
Context.prototype.state='suspended';
let gesture=false, resumes=0;
Context.prototype.resume=function(){assert.ok(gesture,'resume must run inside gesture');resumes++;this.state='running';return Promise.resolve();};
Context.prototype.createBuffer=function(){return {getChannelData(){return new Float32Array(20);}};};
vm.runInThisContext(fs.readFileSync(process.argv[3],'utf8'));
window.AtlasInertia={release(){return {x:0,y:0};}};
window.THREE={WebGLRenderer:class {constructor(){throw Error('no WebGL');}}};
const button=Object.assign(events(),{setAttribute(){},remove(){}});
document.createElement=()=>button;
const element=Object.assign(events(),{parentNode:{insertBefore(){}},classList:{remove(){},add(){}},setPointerCapture(){}});
const cv=events(), reduced=Object.assign(events(),{matches:true});
vm.runInThisContext(fs.readFileSync(process.argv[2],'utf8'));
(async()=>{
 const crystal=window.createAtlasCrystal(element,cv,reduced,()=> 'theory');
 assert.ok(element.handlers.pointerdown,'renderer failure preserves pointer handlers');
 gesture=true;
 element.handlers.pointerdown({type:'pointerdown',isTrusted:true,pointerId:1,clientX:0,clientY:0});
 gesture=false;
 assert.equal(contexts,2,'both contexts created during gesture before fetch completes');
 assert.equal(resumes,2);
 crystal.draw(); crystal.draw();
 await flush(); finishDecode(); await flush();
 assert.equal(sources.length,1,'reduced motion preserves direct press audio');
 assert.ok(sources[0].started && !sources[0].stopped);
 element.handlers.pointerup({pointerId:1});
 assert.ok(sources[0].stopped);
 button.handlers.click({type:'click',isTrusted:true});
 latestContext.state='suspended';
 gesture=true;
 button.handlers.click({type:'click',isTrusted:true});
 gesture=false;
 assert.equal(resumes,4,'unmute synchronously resumes both engines');
 crystal.dispose();
})().catch(e=>{console.error(e);process.exitCode=1;});
"""
    result = subprocess.run(["node", "-e", harness, str(STATIC / "crystal-audio.js"),
                             str(STATIC / "crystal.js"), str(STATIC / "metal-ball-audio.js")], capture_output=True,
                            text=True, timeout=15)
    assert result.returncode == 0, result.stdout + result.stderr
