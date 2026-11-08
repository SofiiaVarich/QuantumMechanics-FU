'use strict';
window.createAtlasMiniCrystals = function (spheres) {
const THREE=window.THREE; let rd,g,mat,disposed=false;
function dispose(){if(disposed)return;disposed=true;spheres.forEach(s=>s.classList?.remove('mini-ready'));g?.dispose();mat?.dispose();if(rd){rd.domElement.removeEventListener('webglcontextlost',dispose);rd.dispose();rd.forceContextLoss();}}
if(!THREE)return {draw(){},dispose};
try{
const VS=`uniform float uT;varying vec3 vV,vO;
float h3(vec3 p){return fract(sin(dot(p,vec3(12.9898,78.233,37.719)))*43758.5453);}
float n3(vec3 p){vec3 i=floor(p),f=fract(p);f=f*f*(3.-2.*f);
return mix(mix(mix(h3(i),h3(i+vec3(1.,0.,0.)),f.x),mix(h3(i+vec3(0.,1.,0.)),h3(i+vec3(1.,1.,0.)),f.x),f.y),
mix(mix(h3(i+vec3(0.,0.,1.)),h3(i+vec3(1.,0.,1.)),f.x),mix(h3(i+vec3(0.,1.,1.)),h3(i+vec3(1.,1.,1.)),f.x),f.y),f.z);}
void main(){vec3 d=normalize(position);float lon=length(d.xz)>1e-4?atan(d.z,d.x):0.;float lat=asin(clamp(d.y,-1.,1.));
float ph=2.*lon+13.*lat+2.4*(n3(d*1.6+vec3(3.,0.,0.))-.5)+2.2*n3(d*1.1+vec3(0.,7.,0.))+uT*1.3;
float s=fract(ph/6.28318);float prof=pow(s,.75)*(1.-smoothstep(.86,1.,s));float pole=1.-.6*pow(abs(d.y),8.);
float r=1.+.075*prof*pole+.02*(n3(d*3.+vec3(9.,0.,0.))-.5);
vO=d;vec4 mv=modelViewMatrix*vec4(d*r,1.);vV=mv.xyz;gl_Position=projectionMatrix*mv;}`;
const FS=`precision highp float;uniform float uT,uWarm;uniform vec3 uLd;varying vec3 vV,vO;
float hs(vec3 p){return fract(sin(dot(p,vec3(12.9898,78.233,37.719)))*43758.5453);}
float vz(vec3 p){vec3 i=floor(p),f=fract(p);f=f*f*(3.-2.*f);
return mix(mix(mix(hs(i),hs(i+vec3(1.,0.,0.)),f.x),mix(hs(i+vec3(0.,1.,0.)),hs(i+vec3(1.,1.,0.)),f.x),f.y),
mix(mix(hs(i+vec3(0.,0.,1.)),hs(i+vec3(1.,0.,1.)),f.x),mix(hs(i+vec3(0.,1.,1.)),hs(i+vec3(1.,1.,1.)),f.x),f.y),f.z);}
vec3 env(vec3 r){float s=sin(r.x*3.1+r.y*2.2+.8)+.5*sin(r.x*7.+r.z*3.);float w=smoothstep(-.5,.7,s);
vec3 c=mix(vec3(.02,.03,.07),vec3(.93,.96,1.),w);
float kd=max(dot(r,uLd),0.);c+=vec3(1.)*pow(kd,14.)*1.8;
c=mix(c,vec3(.04,.12,.92),(1.-smoothstep(-.8,.0,r.x+.25*r.y))*(.75-.45*uWarm)*(1.-.5*w));
c+=vec3(.95,.5,.15)*pow(max(dot(r,normalize(vec3(-.8,-.35,.45))),0.),9.)*(.25+.9*uWarm);
c+=vec3(.2,.8,1.)*pow(max(dot(r,normalize(vec3(.3,-.8,.5))),0.),8.)*.5;return c;}
void main(){
vec3 N=normalize(cross(dFdx(vV),dFdy(vV)));vec3 V=normalize(-vV);float NdV=clamp(dot(N,V),0.,1.);vec3 R=reflect(-V,N);
vec3 e=env(R);vec3 col=e*vec3(.93,.96,1.);
float edge=smoothstep(.06,.28,length(fwidth(N)));
float ph=dot(R,uLd)*1.2+NdV*1.8+vz(vO*4.)*.7+uT*.02;
vec3 rb=.5+.5*cos(6.28318*(ph+vec3(0.,.33,.67)));rb=mix(rb,vec3(.1,.35,1.),.3);
float fres=pow(1.-NdV,2.5);
col=mix(col,rb*(.6+e*.8),clamp(edge*.85+fres*.45,0.,.9));
col+=fres*vec3(.85,.92,1.)*.3;gl_FragColor=vec4(pow(col,vec3(.92)),1.);}`;

const atlas=document.createElement('canvas'),T=128,W=5*T,H=4*T;
rd=new THREE.WebGLRenderer({canvas:atlas,alpha:true,antialias:true});rd.setPixelRatio(1);rd.setSize(W,H,false);rd.setClearColor(0,0);rd.autoClear=false;
atlas.addEventListener('webglcontextlost',dispose);
const scene=new THREE.Scene(),cam=new THREE.PerspectiveCamera(30,1,.1,20);cam.position.z=4.3;cam.updateMatrixWorld();
const U={uT:{value:0},uWarm:{value:0},uLd:{value:new THREE.Vector3(-.5,.6,.65).normalize()}};
g=new THREE.SphereGeometry(1,110,70);mat=new THREE.ShaderMaterial({uniforms:U,vertexShader:VS,fragmentShader:FS,extensions:{derivatives:true}});
const mesh=new THREE.Mesh(g,mat);scene.add(mesh);
let seed=3;const random=()=>(seed=(seed*16807)%2147483647)/2147483647;
const tiles=spheres.map((sphere,n)=>({sphere,n,ctx:sphere.querySelector('canvas').getContext('2d'),rx:(random()-.5)*2.4,ry:random()*6.28,rz:(random()-.5)*1.2,w:(random()-.5)*.5,lx:-.5+(random()-.5)*.6,ly:.55+(random()-.5)*.4,t0:random()*40}));let last=-Infinity;
function draw(now=0){if(disposed||(now>=last&&now-last<33))return;last=now;rd.setScissorTest(false);rd.clear();rd.setScissorTest(true);
for(const {sphere,n,ctx,rx,ry,rz,w,lx,ly,t0} of tiles){if(!ctx)continue;const x=n%5*T,y=Math.floor(n/5)*T,sec=now/1000;
rd.setViewport(x,H-y-T,T,T);rd.setScissor(x,H-y-T,T,T);mesh.rotation.set(rx,ry+w*sec,rz);
U.uT.value=t0+sec;U.uWarm.value=sphere.dataset.category==='experiment'?.9:.05;
U.uLd.value.set(lx+.15*Math.sin(sec*.5+n),ly,.65).normalize();
rd.render(scene,cam);ctx.clearRect(0,0,92,92);ctx.drawImage(atlas,x,y,T,T,0,0,92,92);sphere.classList.add('mini-ready');}}
return {draw,dispose};
}catch(error){dispose();return {draw(){},dispose};}
};
