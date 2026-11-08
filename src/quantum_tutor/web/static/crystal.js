'use strict';
const crystalScriptURL = document.currentScript?.src || new URL('crystal.js', window.location.href).href;
// Shader and shard geometry adapted from the supplied Crystal Atlas reference.
// Requires the reference's pinned Three.js r128; CSS remains the fallback.
window.createAtlasCrystal = function (element, cv, reduced, getMode) {
  const listeners = [];
  let audio = null, soundButton = null, disposed = false, audioTime = 0;
  let metal = null, rollingReady = false, rollingToken = 0, dragSpeed = 0, dragTime = 0;
  let muted = false;
  try { muted = localStorage.getItem('crystal-muted') === 'true'; } catch (_) {}
  function attachMetalAudio() {
    if (!disposed && !metal && window.MetalBallAudio) {
      metal = new window.MetalBallAudio({ maxVoices: 1 });
      metal.setMuted(audio ? audio.muted : muted);
    }
  }
  function roll(speed) {
    if (!rollingReady || disposed || reduced.matches || document.hidden) return;
    metal?.setRolling('crystal', { velocity: Math.min(1, Math.abs(speed) / 8), x: .5 });
  }
  function attachAudio() {
    if (disposed || audio || !window.createCrystalAudio) return;
    audio = window.createCrystalAudio();
    muted = audio.muted;
    metal?.setMuted(muted);
    if (!element.parentNode || !document.createElement) return;
    soundButton = document.createElement('button');
    soundButton.type = 'button';
    soundButton.className = 'crystal-sound-toggle';
    const label = () => {
      soundButton.textContent = audio.muted ? 'Sound off' : 'Sound on';
      soundButton.setAttribute('aria-label', 'Crystal sound');
      soundButton.setAttribute('aria-pressed', String(!audio.muted));
    };
    soundButton.addEventListener('click', e => { muted = !audio.muted; audio.setMuted(muted); metal?.setMuted(muted); if (muted) { rollingReady = false; rollingToken++; } else { audio.unlock(e); attachMetalAudio(); metal?.unlock(e); } label(); });
    label();
    element.parentNode.insertBefore(soundButton, element.nextSibling);
  }
  attachMetalAudio();
  if (window.createCrystalAudio) attachAudio();
  else if (typeof document !== 'undefined' && document.createElement && document.head) {
    if (!window.crystalAudioReady) window.crystalAudioReady = new Promise(resolve => {
      const script = document.createElement('script');
      script.src = new URL('crystal-audio.js', crystalScriptURL).href;
      script.onload = resolve; script.onerror = resolve;
      document.head.appendChild(script);
    });
    window.crystalAudioReady.then(attachAudio);
  }
  const core = { addEventListener(type, fn) { element.addEventListener(type, fn); listeners.push([type, fn]); }, setPointerCapture(id) { element.setPointerCapture(id); } };
  const THREE = window.THREE;
  let drawImpl = null, rdCleanup = null;
  let cd=false, press=false, hit=false, lx=0, ly=0, vx=0, vy2=0;
  let pointer=null, samples=[], previous=null;
  function stop() { rollingToken++; rollingReady=false; dragSpeed=0; metal?.stopAll(); audio?.end(true); cd=press=hit=false; vx=vy2=0; samples=[]; previous=null; if(pointer!==null && element.hasPointerCapture?.(pointer)) element.releasePointerCapture(pointer); pointer=null; }
  let reduce = reduced.matches, mode = getMode();
  function draw() { reduce = reduced.matches; mode = getMode(); if ((typeof document !== 'undefined' && document.hidden)) stop(); if (drawImpl) drawImpl(); }
  const hidden = () => { if (document.hidden) stop(); };
  const reducedChanged = () => { if (reduced.matches) { vx=vy2=0; metal?.stopAll(); } };
  if (typeof document !== 'undefined') document.addEventListener('visibilitychange', hidden);
  window.addEventListener?.('pagehide', stop);
  reduced.addEventListener?.('change', reducedChanged);
  function dispose() {
    disposed = true;
    stop();
    audio?.dispose();
    metal?.dispose();
    if (typeof document !== 'undefined') document.removeEventListener('visibilitychange', hidden);
    window.removeEventListener?.('pagehide', stop);
    reduced.removeEventListener?.('change', reducedChanged);
    soundButton?.remove();
    listeners.forEach(([type, fn]) => element.removeEventListener(type, fn));
        cv.removeEventListener('webglcontextlost', dispose);
    if (rdCleanup) { rdCleanup(); rdCleanup=null; }
    drawImpl = null;
    element.classList.remove('webgl-ready');
  }
  let aim = () => { hit=true; };
  let moveVisual = () => {}, releaseVisual = () => {};
  if (THREE) try {
const VS=`uniform vec3 uPt;uniform float uAmp,uWave,uT;varying vec3 vV,vO;varying float vG;
void main(){vec3 dir=normalize(position);float d=distance(dir,uPt);float g=exp(-d*d/.2);
float disp=-uAmp*.30*g+uWave*.09*sin(d*14.-uT*8.)*exp(-d*1.4);
vec3 p=position+dir*disp;vO=position;vG=g*uAmp;vec4 mv=modelViewMatrix*vec4(p,1.);vV=mv.xyz;gl_Position=projectionMatrix*mv;}`;
const FS=`precision highp float;uniform float uT,uMix;uniform vec3 uAcc,uDeep,uSil,uTch;varying vec3 vV,vO;varying float vG;
float hs(vec3 p){return fract(sin(dot(p,vec3(12.9898,78.233,37.719)))*43758.5453);}
vec3 hue(vec3 c,float a){const vec3 k=vec3(.57735);float ca=cos(a),sa=sin(a);return c*ca+cross(k,c)*sa+k*dot(k,c)*(1.-ca);}
vec3 env(vec3 r){float up=r.y*.5+.5;vec3 c=mix(uDeep*.55,vec3(.80,.88,1.),smoothstep(.1,1.,up));
c+=vec3(1.,.97,.92)*pow(max(dot(r,normalize(vec3(-.5,.7,.6))),0.),14.)*1.6;
c+=vec3(.6,.7,1.)*pow(max(dot(r,normalize(vec3(.7,.2,.7))),0.),9.)*.9;
c+=vec3(.9,.6,1.)*pow(max(dot(r,normalize(vec3(.1,-.6,.8))),0.),7.)*.6;
c*=.72+.4*smoothstep(.2,.8,abs(sin(r.x*5.+r.y*3.)));return c;}
void main(){
if(!gl_FrontFacing){gl_FragColor=vec4(vec3(.05,.07,.11)*(.6+hs(floor(vO*9.))),1.);return;}
vec3 N=normalize(cross(dFdx(vV),dFdy(vV)));vec3 V=normalize(-vV);float NdV=clamp(dot(N,V),0.,1.);vec3 R=reflect(-V,N);
float fr=hs(floor(N*18.));vec3 e=env(R);vec3 metal=mix(uSil,uAcc,.18)*e*.95;
float ph=NdV*2.2+fr*1.6+vO.y*.8+uT*.12;
float t1=.5+.5*sin(ph*6.),t2=.5+.5*sin(ph*3.+1.);
vec3 iri=mix(uDeep,uAcc,.3+.7*t1);iri=mix(iri,mix(uAcc,vec3(1.),.5),smoothstep(.72,1.,t2)*.7);
iri=mix(iri,uTch,clamp(vG*1.2,0.,1.));
float amt=smoothstep(.1,.8,NdV)*(.5+.5*fr)*uMix;
vec3 lit=iri*(.45+e*.85);vec3 col=mix(metal,lit,clamp(amt+vG*.5,0.,1.));
col+=pow(1.-NdV,3.)*vec3(.35,.4,.5)*.35;col+=vG*.18;gl_FragColor=vec4(pow(col,vec3(.9)),1.);}`;
const vn=(()=>{const h=(x,y,z)=>{const n=Math.sin(x*127.1+y*311.7+z*74.7)*43758.5453;return n-Math.floor(n)},l=(a,b,t)=>a+(b-a)*t,u=t=>t*t*(3-2*t);
return(x,y,z)=>{const ix=Math.floor(x),iy=Math.floor(y),iz=Math.floor(z),fx=u(x-ix),fy=u(y-iy),fz=u(z-iz);
return l(l(l(h(ix,iy,iz),h(ix+1,iy,iz),fx),l(h(ix,iy+1,iz),h(ix+1,iy+1,iz),fx),fy),l(l(h(ix,iy,iz+1),h(ix+1,iy,iz+1),fx),l(h(ix,iy+1,iz+1),h(ix+1,iy+1,iz+1),fx),fy),fz)}})();
const rd=new THREE.WebGLRenderer({canvas:cv,alpha:true,antialias:true});rdCleanup = () => { rd.dispose(); rd.forceContextLoss(); };rd.setPixelRatio(Math.min(devicePixelRatio||1,2));rd.setSize(250,250,false);rd.setClearColor(0,0);
const scn=new THREE.Scene(),cam=new THREE.PerspectiveCamera(30,1,.1,20);cam.position.z=5.2;cam.updateMatrixWorld();
const g=new THREE.IcosahedronGeometry(1,10),pos=g.attributes.position,P=pos.array,v=new THREE.Vector3();
for(let i=0;i<pos.count;i++){v.fromArray(P,i*3).normalize();
v.x+=(vn(v.x*9+3,v.y*9,v.z*9)-.5)*.07;v.y+=(vn(v.x*9,v.y*9+5,v.z*9)-.5)*.07;v.z+=(vn(v.x*9,v.y*9,v.z*9+9)-.5)*.07;v.normalize();
const f=vn(v.x*1.8+11,v.y*1.8,v.z*1.8)+.5*vn(v.x*3.6,v.y*3.6+4,v.z*3.6)+.25*vn(v.x*7,v.y*7,v.z*7+8);
let rg=1-Math.abs(2*vn(v.x*4.5+7,v.y*4.5,v.z*4.5+2)-1);rg*=rg;
const r2=1-Math.abs(2*vn(v.x*11+3,v.y*11,v.z*11+6)-1);v.multiplyScalar(.95+.14*(f/1.75-.5)+.13*(rg-.35)+.05*(r2*r2-.35)).toArray(P,i*3)}
for(let t=0;t<pos.count;t+=3){const cx_=(P[t*3]+P[t*3+3]+P[t*3+6])/3,cy_=(P[t*3+1]+P[t*3+4]+P[t*3+7])/3,cz_=(P[t*3+2]+P[t*3+5]+P[t*3+8])/3;
const n=Math.sin(Math.round(cx_*60)*12.9+Math.round(cy_*60)*78.2+Math.round(cz_*60)*37.7)*43758.5,k=1+((n-Math.floor(n))-.5)*.05;for(let j=0;j<9;j++)P[t*3+j]*=k}
pos.needsUpdate=true;
const U={uT:{value:0},uAcc:{value:new THREE.Color('#343F91')},uDeep:{value:new THREE.Color('#343F91')},uSil:{value:new THREE.Color('#C9D8EA')},uTch:{value:new THREE.Color('#477BFF')},uMix:{value:.4},uPt:{value:new THREE.Vector3(0,0,1)},uAmp:{value:0},uWave:{value:0}};
const mesh=new THREE.Mesh(g,new THREE.ShaderMaterial({uniforms:U,vertexShader:VS,fragmentShader:FS,side:THREE.DoubleSide,extensions:{derivatives:true}}));
const releaseRenderer = rdCleanup; rdCleanup = () => { g.dispose(); mesh.material.dispose(); releaseRenderer(); };
mesh.rotation.set(-.3,.6,0);scn.add(mesh);
const ray=new THREE.Raycaster(),sph=new THREE.Sphere(new THREE.Vector3(),1.05),hp=new THREE.Vector3();
aim = function(e){const r=cv.getBoundingClientRect();ray.setFromCamera({x:((e.clientX-r.left)/r.width)*2-1,y:-(((e.clientY-r.top)/r.height)*2-1)},cam);mesh.updateMatrixWorld();
if(ray.ray.intersectSphere(sph,hp)){mesh.worldToLocal(hp);U.uPt.value.copy(hp).normalize();hit=true}else hit=false}
let amp=0,ampV=0,wave=0,t=0,rotUntil=0,mixCur=1,loadUntil=performance.now()+1200;const CC={sil:'#C9D8EA',touch:'#477BFF',rot:'#9470E8',chap:'#56D9E8',exp:'#73D8B8',load:'#343F91'},tgt=new THREE.Color();
drawImpl=()=>{const clock=performance.now(),dt=previous===null?0:(clock-previous)/1000;previous=clock;t+=reduce?0:dt;
if(reduce){vx=vy2=0;}
if(!cd){const x=window.AtlasInertia.step(vx,dt),y=window.AtlasInertia.step(vy2,dt);mesh.rotation.y+=x.delta;mesh.rotation.x+=y.delta;vx=x.velocity;vy2=y.velocity;}
if (cd) roll(clock-dragTime <= 120 ? dragSpeed : 0); else roll(Math.sign(Math.abs(vx)>=Math.abs(vy2)?vx:vy2)*Math.hypot(vx,vy2));
const target=(press&&hit)?1:hit?.25:0;
if(reduce)amp=target;else{ampV+=(target-amp)*.14;ampV*=.76;amp+=ampV}
wave*=.95;const now=performance.now();let key='sil',mx=.4;if(now<loadUntil){key='load';mx=1}else if(now<rotUntil){key='rot';mx=1}else if(hit||press){key='touch';mx=1}else if(mode==='theory'){key='chap';mx=.9}else if(mode==='experiment'){key='exp';mx=.9}tgt.set(CC[key]);U.uAcc.value.lerp(tgt,reduce?1:.08);mixCur+=(mx-mixCur)*.08;
U.uT.value=t;U.uAmp.value=amp;U.uWave.value=wave;U.uMix.value=mixCur;rd.render(scn,cam)};
moveVisual = (dx,dy) => { mesh.rotation.y+=dx*.01; mesh.rotation.x+=dy*.01; rotUntil=performance.now()+500; };
releaseVisual = () => { wave=1; };
drawImpl();

    element.classList.add('webgl-ready');
    cv.addEventListener('webglcontextlost', dispose);
  } catch (_) { if (rdCleanup) { rdCleanup(); rdCleanup=null; } drawImpl=null; aim=()=>{hit=true;}; moveVisual=()=>{}; releaseVisual=()=>{}; }
  core.addEventListener('pointerdown',e=>{if(pointer!==null)return;stop();pointer=e.pointerId;cd=press=true;audioTime=performance.now();lx=e.clientX;ly=e.clientY;samples=[{x:lx,y:ly,t:performance.now()}];aim(e);if(hit && e.isTrusted === true && e.type === 'pointerdown' && !document.hidden){audio?.begin(e);attachMetalAudio();const token=++rollingToken; if(metal) metal.unlock(e).then(ok=>{if(ok && token===rollingToken && !disposed && !document.hidden && !metal.muted)rollingReady=true;}).catch(()=>{});}core.setPointerCapture(e.pointerId);draw()});
core.addEventListener('pointermove',e=>{if(pointer!==null&&e.pointerId!==pointer)return;aim(e);if(cd){const dx=e.clientX-lx,dy=e.clientY-ly;moveVisual(dx,dy);lx=e.clientX;ly=e.clientY;const now=performance.now();audio?.update({speed:Math.hypot(dx,dy)*1000/Math.max(1,now-audioTime),pressure:e.pressure || .5});dragSpeed=Math.hypot(dx,dy)*.01*1000/Math.max(1,now-audioTime);dragTime=now;audioTime=now;samples.push({x:lx,y:ly,t:now});samples=samples.filter(s=>now-s.t<=120);}draw()});
core.addEventListener('pointerup',e=>{if(e.pointerId!==pointer)return;audio?.end();const velocity=window.AtlasInertia.release(samples,performance.now(),reduced.matches);cd=press=false;pointer=null;samples=[];vx=velocity.x;vy2=velocity.y;releaseVisual();draw()});
core.addEventListener('pointerleave',()=>{if(!cd)hit=false});
core.addEventListener('pointercancel',stop);core.addEventListener('lostpointercapture',()=>{if(pointer!==null)stop();});
  return { draw, dispose, stop, attachMetalAudio };
};
