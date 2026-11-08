"""Exercise the classic metallic synthesis engine without browser audio hardware."""
import shutil
import subprocess
from pathlib import Path

import pytest

STATIC = Path(__file__).resolve().parents[1] / 'src/quantum_tutor/web/static'


def test_metal_engine():
    if not shutil.which('node'):
        pytest.skip('Node required for Web Audio mocks')
    harness = r"""
const assert = require('node:assert/strict');
const fs = require('node:fs'), vm = require('node:vm');
global.window = {};
let contexts=0, nodes=[], resume;
const param=()=>({value:0,setTargetAtTime(v){assert.ok(Number.isFinite(v));this.value=v;},setValueAtTime(v){this.value=v;},exponentialRampToValueAtTime(v){assert.ok(Number.isFinite(v));}});
function node(){const n={gain:param(),frequency:param(),Q:param(),connect(){return this;},disconnect(){this.disconnected=true;},start(){this.started=true;},stop(){this.stopped=true;}};nodes.push(n);return n;}
class Context {
 constructor(){contexts++;this.state='suspended';this.currentTime=0;this.sampleRate=100;this.destination={};}
 createGain(){return node();} createBufferSource(){return node();} createBiquadFilter(){return node();} createOscillator(){return node();}
 createBuffer(){return {getChannelData(){return new Float32Array(200);}};}
 resume(){return new Promise(resolve=>{resume=()=>{this.state='running';resolve();};});}
 close(){this.closed=true;return Promise.resolve();}
}
window.AudioContext=Context;
vm.runInThisContext(fs.readFileSync(process.argv[1],'utf8'));
(async()=>{
 const a=new window.MetalBallAudio({maxVoices:2});
 assert.equal(contexts,0);
 assert.equal(await a.unlock({isTrusted:false,type:'pointerdown'}),false);
 assert.equal(await a.unlock({isTrusted:false,type:'click'}),false);
 const pending=a.unlock({isTrusted:true,type:'pointerdown'});resume();assert.equal(await pending,true);
 assert.equal(contexts,1);
 a.setRolling('a',{velocity:1,x:NaN});
 const roll=a.rolling.get('a');assert.ok(roll.source.started);assert.equal(roll.gain.gain.value,.045);
 a.setRolling('a',{velocity:.2});assert.ok(roll.gain.gain.value<.045);
 a.setRolling('b',{velocity:1});a.setRolling('c',{velocity:1});assert.equal(a.rolling.size,2);
 a.setRolling('a',{velocity:NaN});assert.ok(roll.source.stopped);assert.ok(roll.filter.disconnected);
 a.impact('hit',{intensity:Infinity});assert.equal(a.voices.size,1);
 a.setMuted(true);assert.equal(a.voices.size,0);assert.equal(a.rolling.size,0);assert.equal(a.timers.size,0);
 a.setMuted(false);assert.equal(a.rolling.size,0);
 await a.dispose();assert.ok(nodes.every(n=>n.disconnected));
 assert.equal(await a.unlock({isTrusted:true,type:'pointerdown'}),false);
 const b=new window.MetalBallAudio();const late=b.unlock({isTrusted:true,type:'pointerdown'});await b.dispose();resume();assert.equal(await late,false);
 const toggle=b.unlock({isTrusted:true,type:'click'});assert.equal(await toggle,false);
 const c=new window.MetalBallAudio();c.unlock({isTrusted:true,type:'pointerdown'});resume();await Promise.resolve();await c.dispose();
})().catch(e=>{console.error(e);process.exitCode=1;});
"""
    subprocess.run(['node', '-e', harness, str(STATIC / 'metal-ball-audio.js')], check=True, capture_output=True, text=True, timeout=15)
