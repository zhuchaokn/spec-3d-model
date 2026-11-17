/* Six spoken chapters, multiple directed shots. Geometry is a display copy in cm. */
const data=window.STORY_DATA,slides=[...document.querySelectorAll('.slide')],stage=document.querySelector('#stage'),button=document.querySelector('#play');
const exportMode=new URLSearchParams(location.search).has('export');
let insetTextureReady=Promise.resolve(true);
let current=0,playing=false,started=false,ended=false,elapsed=0,last=performance.now(),idle=0;
const total=data.reduce((s,d)=>s+d.duration,0),audio=new Audio();audio.preload='none';const offsets=data.map((_,i)=>data.slice(0,i).reduce((sum,d)=>sum+d.duration,0));let audioKey=-1,playGeneration=0,starting=false;
let modelPromise,renderer,scene,camera,root,models=[],provinces=[],bases=[],seas=[],lid,renderHost,inset,dimension,axes,shot='intro',grow=1,split=0,sink=0;
// Extend action durations by 20%, without stretching the narration clock.
const MOTION_SCALE=1.2;
function motion(seconds){return seconds*MOTION_SCALE;}
function clamp(x){return Math.max(0,Math.min(1,x));}function ease(x){x=clamp(x);return x*x*(3-2*x);}function fast(x){return 1-Math.pow(1-clamp(x),4);}function snap(x){x=clamp(x);return x===1?1:1+2.4*Math.pow(x-1,3)+1.4*Math.pow(x-1,2);}function mix(a,b,q){return a+(b-a)*q;}function set(el,key,v){el.style.setProperty(key,v);}function html(sel,text){const el=document.querySelector(sel);if(el.innerHTML!==text)el.innerHTML=text;}
function notify(text){const el=document.querySelector('#audio-notice');el.textContent=text;el.hidden=false;setTimeout(()=>el.hidden=true,6500);}
function images(i){for(const img of slides[i].querySelectorAll('img[data-src]')){img.src=img.dataset.src;delete img.dataset.src;}}
function loadScript(src){return new Promise((resolve,reject)=>{const s=document.createElement('script');s.src=src;s.onload=resolve;s.onerror=()=>reject(new Error('无法加载 '+src));document.head.appendChild(s);});}
async function prepareModel(){if(modelPromise)return modelPromise;modelPromise=(async()=>{
await loadScript('assets/three.min.js');await loadScript('assets/cinema-mesh.js');
renderer=new THREE.WebGLRenderer({antialias:true,alpha:true,preserveDrawingBuffer:exportMode});renderer.setPixelRatio(exportMode?1:Math.min(devicePixelRatio,1.6));renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.setClearColor(0,0);renderer.localClippingEnabled=true;renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap;
scene=new THREE.Scene();camera=new THREE.PerspectiveCamera(32,1,.1,300);scene.add(new THREE.HemisphereLight(0xf2ffdd,0x103c2a,1.8));
const key=new THREE.DirectionalLight(0xfff1cf,3.2);key.position.set(-25,55,30);key.castShadow=true;key.shadow.mapSize.set(1024,1024);Object.assign(key.shadow.camera,{left:-40,right:40,top:40,bottom:-40,near:1,far:130});key.shadow.bias=-.00015;key.shadow.normalBias=.015;scene.add(key);
const rim=new THREE.DirectionalLight(0x72b4b6,1.4);rim.position.set(30,18,-30);scene.add(rim);root=new THREE.Group();root.rotation.x=-Math.PI/2;scene.add(root);
const bounds=CINEMA_MESH.bounds,cx=(bounds[0]+bounds[2])/2,cy=(bounds[1]+bounds[3])/2;
for(const d of CINEMA_MESH.meshes){const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(d.vertices.flatMap(v=>[v[0]-cx,v[1]-cy,v[2]]),3));g.setIndex(d.indices);g.computeVertexNormals();g.computeBoundingBox();const m=new THREE.MeshStandardMaterial({color:d.color,roughness:d.kind==='sea'?.43:.78,metalness:d.kind==='sea'?.08:0,side:THREE.FrontSide,transparent:false,opacity:1});const mesh=new THREE.Mesh(g,m);mesh.userData={...d,cx:d.center[0]-cx,cy:d.center[1]-cy};mesh.castShadow=d.kind==='province'||d.kind==='base';mesh.receiveShadow=true;root.add(mesh);models.push(mesh);if(d.kind==='province')provinces.push(mesh);else if(d.kind==='sea')seas.push(mesh);else if(d.kind==='lid')lid=mesh;else bases.push(mesh);}
const ground=new THREE.Mesh(new THREE.PlaneGeometry(100,100),new THREE.ShadowMaterial({opacity:.22}));ground.rotation.x=-Math.PI/2;ground.position.y=-.08;ground.receiveShadow=true;scene.add(ground);
let textureLoaded;insetTextureReady=new Promise(resolve=>textureLoaded=resolve);
const ib=CINEMA_MESH.insetBounds,texture=new THREE.TextureLoader().load('assets/cinema-inset.svg',()=>textureLoaded(true),undefined,()=>textureLoaded(false));texture.colorSpace=THREE.SRGBColorSpace;
inset=new THREE.Mesh(new THREE.PlaneGeometry(ib[2]-ib[0],ib[3]-ib[1]),new THREE.MeshBasicMaterial({map:texture,transparent:true,side:THREE.DoubleSide,depthWrite:false}));inset.position.set((ib[0]+ib[2])/2-cx,(ib[1]+ib[3])/2-cy,CINEMA_MESH.dimensions.platform_cm+.105);inset.userData={tile:'Tray_X2_Y1',home:inset.position.clone()};root.add(inset);
// Sparse coordinate guides: short projection / extrusion beat, then clear away.
const guides=[];for(let n=-20;n<=20;n+=5){guides.push(-23,n,-.03,23,n,-.03,n,-23,-.03,n,23,-.03);}guides.push(-9,0,0,-9,0,4,0,0,0,0,0,4,9,0,0,9,0,4);
axes=new THREE.LineSegments(new THREE.BufferGeometry().setAttribute('position',new THREE.Float32BufferAttribute(guides,3)),new THREE.LineBasicMaterial({color:0xa6d8a0,transparent:true,opacity:.3,depthWrite:false}));root.add(axes);
const focus=CINEMA_MESH.recessFocus,fx=focus[0]-cx,fy=focus[1]-cy,floor=CINEMA_MESH.dimensions.floor_cm,top=CINEMA_MESH.dimensions.platform_cm;
const points=[fx,fy,floor,fx,fy,top,fx-.12,fy,top,fx+.12,fy,top,fx-.12,fy,floor,fx+.12,fy,floor];dimension=new THREE.LineSegments(new THREE.BufferGeometry().setAttribute('position',new THREE.Float32BufferAttribute(points,3)),new THREE.LineBasicMaterial({color:0xe4efc7,depthTest:false}));dimension.renderOrder=20;root.add(dimension);
attach();return true;
})().catch(e=>{console.warn(e.message);renderer=undefined;modelPromise=undefined;notify('三维镜头暂时无法加载，将继续使用真实模型截图。');return false;});return modelPromise;}
function attach(){if(!renderer)return;const id=['intro-host',null,'data-host','terrain-host','parts-host','ending-host'][current];if(!id)return;renderHost=document.querySelector('#'+id);renderHost.appendChild(renderer.domElement);renderHost.querySelector('.fallback')?.setAttribute('hidden','');if(current===0)document.querySelector('.hero-image').classList.add('has-model');resize();}
function resize(){if(!renderer||!renderHost)return;const r=renderHost.getBoundingClientRect();if(!r.width||!r.height)return;renderer.setSize(r.width,r.height,false);camera.aspect=r.width/r.height;camera.updateProjectionMatrix();}
new ResizeObserver(resize).observe(stage);window.addEventListener('resize',resize);
async function playAudio(){if(!playing)return;const generation=++playGeneration;audio.preload='auto';if(audioKey<0){const at=offsets[current]+elapsed;audio.src='narration.mp3';audioKey=0;audio.onloadedmetadata=()=>{if(at>0)audio.currentTime=at;};audio.load();}try{await audio.play();}catch(e){if(generation!==playGeneration||!playing)return;playing=false;stage.classList.remove('playing');button.hidden=false;button.innerHTML='<span>▶</span> 继续播放';notify('音频暂时无法播放，请点击继续播放重试。');}}
// Visual chapter cuts share one continuous audio clock; never reload audio on a cut.
function go(i,seek=true){if(i<0||i>=slides.length)return;slides[current].classList.remove('active');current=i;slides[current].classList.add('active');elapsed=0;if(seek&&audioKey>=0)audio.currentTime=offsets[i];images(i);document.querySelector('#counter').textContent=`${String(i+1).padStart(2,'0')} / 06`;attach();if(i>=2&&!renderer)prepareModel();update(0);}
button.onclick=()=>{if(ended){ended=false;stage.classList.remove('ended');go(0);}started=true;playing=true;stage.classList.add('playing');button.hidden=true;last=performance.now();if(!renderer)prepareModel();playAudio();};
audio.addEventListener('ended',()=>{if(playing)finish();});
audio.addEventListener('error',()=>{if(!playing)return;playing=false;stage.classList.remove('playing');button.hidden=false;button.innerHTML='<span>▶</span> 重试播放';audioKey=-1;notify('音频加载失败，请点击重试。');});
function cueTime(i,needle,fallback){return data[i].cues.find(c=>c.text.includes(needle))?.start??fallback*data[i].audio_duration;}
const coastAt=cueTime(3,'再把海岸线',.4),islandAt=cueTime(3,'南海区域',.51),baseAt=cueTime(3,'为了用起来方便',.67),slotAt=cueTime(3,'先加一个带边框',.74),insertAt=cueTime(3,'省份拼进去',.85),sampleAt=cueTime(4,'甚至还细心',.36),filesAt=cueTime(4,'最后',.65);
function show(sel,id){for(const el of document.querySelectorAll(sel))el.classList.toggle('shown',el.id===id);}
function caption(t){const cues=data[current].cues;const c=cues.find(c=>t>=c.start&&t<c.end)||[...cues].reverse().find(c=>t>=c.start)||cues[0];const el=slides[current].querySelector('.subtitle');if(el.textContent!==c.text)el.textContent=c.text;}
function target(x,y,z=.3){if(!window.CINEMA_MESH)return [x,y,z];const b=CINEMA_MESH.bounds;return [x-(b[0]+b[2])/2,y-(b[1]+b[3])/2,z];}
function pose(t,keys){let a=keys[0],b=a;for(let i=1;i<keys.length;i++){b=keys[i];if(t<=b.t){if(b.cut&&t<b.t)return a;const q=ease((t-a.t)/(b.t-a.t));return {el:mix(a.el,b.el,q),az:mix(a.az,b.az,q),dist:mix(a.dist,b.dist,q),target:a.target.map((x,j)=>mix(x,b.target[j],q))};}a=b;}return keys[keys.length-1];}
function cameraPose(p){const e=p.el*Math.PI/180,az=p.az*Math.PI/180,tar=new THREE.Vector3(p.target[0],p.target[2],-p.target[1]);camera.position.set(tar.x+Math.cos(e)*Math.sin(az)*p.dist,tar.y+Math.sin(e)*p.dist,tar.z+Math.cos(e)*Math.cos(az)*p.dist);camera.lookAt(tar);}
function tileOffset(tile,q){return [tile?.includes('X1')?-2.6*q:2.6*q,tile?.includes('Y1')?-2.6*q:2.6*q];}
function resetWorld(){grow=1;split=0;sink=0;root.rotation.x=-Math.PI/2;root.rotation.z=0;axes.visible=false;for(const m of models){m.position.set(0,0,0);m.scale.set(1,1,1);m.material.opacity=1;m.material.clippingPlanes=null;m.material.color.set(m.userData.color);m.visible=m.userData.kind!=='lid';}inset.visible=true;inset.position.copy(inset.userData.home);dimension.visible=false;}
function assemble(){resetWorld();}
function renderScene(t){if(!renderer)return;resetWorld();const duration=data[current].audio_duration,p=clamp(t/duration),zero=[0,0,.3],macro=target(...CINEMA_MESH.macroFocus),focus=target(...CINEMA_MESH.recessFocus,.28);let cp;
if(current===0){shot='intro-macro-pullback';cp=pose(t,[{t:0,el:26,az:-24,dist:19,target:macro},{t:motion(.65),el:31,az:-12,dist:24,target:macro},{t:motion(1.35),el:51,az:9,dist:90,target:zero},{t:6.6,el:51,az:13,dist:90,target:zero}]);}
if(current===2){shot='data-to-flat-map';for(const m of bases)m.visible=false;for(const m of seas)m.visible=false;inset.visible=false;for(const m of provinces){m.scale.z=.025;m.material.color.set('#c8daa8');}cp={el:84,az:0,dist:82,target:zero};}
if(current===3){
 const riseAt=cueTime(3,'把采样海拔',.11),proofAt=cueTime(3,'自动导进',.205),detailAt=cueTime(3,'整张地图',.263);
 grow=fast((t-riseAt)/motion(.60));
 const isProof=t>=proofAt&&t<detailAt,isSea=t>=coastAt&&t<baseAt,isBase=t>=baseAt;
 show('.scene-visual',isProof?'blender-visual':'terrain-visual');
 if(t<coastAt){
  shot=t<motion(.38)?'map-lays-flat':t<riseAt?'xy-projection':t<riseAt+motion(.65)?'z-snap-rise':t<proofAt?'terrain-camera-orbit':isProof?'blender-proof':'mountain-tracking-closeup';
  for(const m of [...bases,...seas])m.visible=false;inset.visible=false;
  root.rotation.x=mix(-.35,-Math.PI/2,fast(t/motion(.38)));
  for(const m of provinces){m.scale.z=.001+.999*grow;m.material.color.set('#cbdbaa');}
  axes.visible=t<proofAt;axes.scale.z=.001+.999*grow;axes.material.opacity=.24*(1-fast((t-proofAt+.3)/motion(.3)));
  cp=pose(t,[
   {t:0,el:48,az:0,dist:84,target:zero},{t:motion(.38),el:84,az:0,dist:83,target:zero},
   {t:riseAt+motion(.70),el:84,az:0,dist:83,target:zero},
   {t:riseAt+motion(1.35),el:19,az:-18,dist:93,target:[0,0,1.1]},
   {t:proofAt,el:19,az:-8,dist:93,target:[0,0,1.1]},
   {t:detailAt,el:19,az:-8,dist:93,target:[0,0,1.1]},
   {t:detailAt+.12,cut:true,el:22,az:-25,dist:25,target:macro},
   {t:detailAt+.12+motion(.68),el:24,az:-15,dist:24,target:macro},
   {t:coastAt-.1,el:24,az:5,dist:25,target:macro}]);
 }
 if(isSea){
  shot=t<islandAt?'ocean-wipe':'south-sea-inset-closeup';
  // Reveal opaque ocean with a world-space wipe; never fade coincident caps.
  const q=fast((t-coastAt)/motion(.48)),half=(CINEMA_MESH.bounds[2]-CINEMA_MESH.bounds[0])/2;
  for(const m of seas){m.visible=q>0;m.material.clippingPlanes=q<1?[new THREE.Plane(new THREE.Vector3(-1,0,0),mix(-half-1,half+1,q))]:null;}
  for(const m of provinces)m.material.color.lerp(new THREE.Color('#cbdbaa'),1-q);
  const it=target((CINEMA_MESH.insetBounds[0]+CINEMA_MESH.insetBounds[2])/2,(CINEMA_MESH.insetBounds[1]+CINEMA_MESH.insetBounds[3])/2,.5);
  cp=pose(t,[{t:coastAt,el:51,az:9,dist:90,target:zero},
   {t:islandAt-.01,el:49,az:0,dist:87,target:zero},
   {t:islandAt-.01+motion(.46),el:68,az:-4,dist:29,target:it},
   {t:baseAt-.01,el:72,az:5,dist:28,target:it}]);
 }
 if(isBase){
  shot=t<slotAt?'cards-snap-lift':t<insertAt?'recess-sinks-2mm':'cards-seat-in-recess';
  sink=fast((t-slotAt-.18)/motion(.42));
  provinces.forEach((m,i)=>{const lift=fast((t-baseAt-i*.005)/motion(.28))*(1-fast((t-insertAt-i*.007)/motion(.32)));m.position.z=4*lift;});
  lid.visible=t<insertAt&&sink<.999;lid.position.z=-CINEMA_MESH.dimensions.slot_depth_cm*sink;
  dimension.visible=t>=slotAt+.12&&t<insertAt;
  cp=pose(t,[{t:baseAt,el:51,az:9,dist:90,target:zero},
   {t:baseAt+motion(.4),el:42,az:13,dist:89,target:zero},
   {t:slotAt,cut:true,el:22,az:35,dist:11,target:focus},
   {t:slotAt+motion(.6),el:19,az:25,dist:10.5,target:focus},
   {t:insertAt-.01,el:19,az:20,dist:10.5,target:focus},
   {t:insertAt,cut:true,el:51,az:9,dist:90,target:zero},
   {t:insertAt+motion(.55),el:47,az:5,dist:87,target:zero},
   {t:duration,el:51,az:9,dist:90,target:zero}]);
 }
 const beat=t<coastAt?0:t<baseAt?1:t<insertAt?2:3;
 const titles=['平面躺下。高度拉起。<br><em>转个角度，看地形。</em>','海岸线，清楚分界。<br><em>南海，完整呈现。</em>','沿地图轮廓。<br><em>凹槽下陷 2 mm。</em>','省份，嵌进去。<br><em>拼成完整地图。</em>'];
 html('#terrain-title',titles[beat]);
 html('#terrain-metrics',[
 `<div><b>XY</b><span>Albers 投影</span></div><div><b>Z × 40</b><span>统一高度放大</span></div><div><b>实体</b><span>三角网格封底</span></div>`,
 `<div><b>海蓝</b><span>真实海洋区域</span></div><div><b>陆地灰</b><span>周边陆地</span></div><div><b>南海</b><span>完整源轮廓附图</span></div>`,
 `<div><b>2 mm</b><span>凹槽深度</span></div><div><b>轮廓槽</b><span>沿国境线形成</span></div><div><b>插板</b><span>抬起，露出底座</span></div>`,
 `<div><b>32</b><span>省份插板</span></div><div><b>0.15 mm</b><span>单侧装配公差</span></div><div><b>拼装</b><span>插板嵌入底座</span></div>`][beat]);
 document.querySelectorAll('.beat-track i').forEach((el,i)=>el.classList.toggle('done',i<=beat));
 document.querySelector('.height-chip').hidden=beat!==0;document.querySelector('#height-value').textContent='× '+Math.round(1+39*grow);
 document.querySelector('#shot-note').textContent=({'map-lays-flat':'落平 / XY 投影','xy-projection':'XY 坐标 / 平面网格','z-snap-rise':'Z 轴拉升 / × 40','terrain-camera-orbit':'低角度转镜 / 地形全景','mountain-tracking-closeup':'山脉近景 / 侧向移动','ocean-wipe':'真实海岸线 / 海蓝扫入','south-sea-inset-closeup':'右下角附图 / 南海诸岛','cards-snap-lift':'插板抬起 / 露出底座','recess-sinks-2mm':'下陷 2 mm / 近景观察','cards-seat-in-recess':'插板落入 / 完成拼装'})[shot]||'BLENDER / 真实界面';
 document.querySelector('#dimension-note').hidden=!dimension.visible;document.querySelector('#inset-note').hidden=shot!=='south-sea-inset-closeup';
}
if(current===4){
 const splitAt=2.15,fadeAt=1.8;
 split=snap((t-splitAt)/motion(.44));
 shot=t<splitAt?'province-explode':t<sampleAt?'four-base-tiles':t<filesAt?'bambu-and-fit-coupon':'deliverable-files';
 provinces.forEach((m,i)=>{const stagger=i*.004,lift=fast((t-.10-stagger)/motion(.24)),spread=snap((t-.42-stagger)/motion(.38)),r=Math.hypot(m.userData.cx,m.userData.cy)||1;m.position.set(m.userData.cx/r*spread*4.5,m.userData.cy/r*spread*4.5,4*lift);m.visible=t<fadeAt+i*.007;});
 for(const m of [...bases,...seas]){const off=tileOffset(m.userData.tile,split);m.position.set(off[0],off[1],0);}
 const off=tileOffset(inset.userData.tile,split);inset.position.x+=off[0];inset.position.y+=off[1];
 cp=pose(t,[{t:0,el:51,az:9,dist:90,target:zero},{t:motion(.9),el:55,az:13,dist:99,target:[0,0,1]},
  {t:splitAt,el:57,az:10,dist:98,target:zero},{t:splitAt+motion(.6),el:79,az:0,dist:93,target:zero},
  {t:sampleAt,el:79,az:0,dist:93,target:zero}]);
 show('.parts-visual,.print-visual,.file-stage',t<sampleAt?'parts-visual':t<filesAt?'print-visual':'file-visual');
 html('#parts-title',t<splitAt?'按省拆开。<br><em>插板，快速分离。</em>':t<sampleAt?'底座，分成四片。<br><em>每片，都能上打印床。</em>':t<filesAt?'拓竹工程就绪。<br><em>先试配，再打整套。</em>':'拿到一整套文件。<br><em>3MF · BLEND · STL</em>');
 document.querySelector('#parts-shot-note').textContent=t<splitAt?'省份抬起 → 径向拆开':'四片底座展开 / 每片最大约 238 × 238 mm';
 const count=document.querySelector('.parts-count');count.querySelector('b').textContent=t<splitAt?'32':'4';count.querySelector('span').textContent=t<splitAt?'省份插板':'底座分片';
 set(document.querySelector('.sample'),'--sample',fast((t-sampleAt-.12)/motion(.28)));
 document.querySelectorAll('.files>div').forEach((el,i)=>set(el,'--file',fast((t-filesAt-i*.10)/motion(.24))));
}
if(current===5){shot='ending-return-to-model';cp=pose(t,[{t:0,el:51,az:9,dist:90,target:zero},{t:duration,el:49,az:-4,dist:86,target:zero}]);}
if(cp)cameraPose(cp);root.updateMatrixWorld(true);camera.updateMatrixWorld(true);
if(current===3&&dimension.visible){const f=CINEMA_MESH.recessFocus,b=CINEMA_MESH.bounds,v=new THREE.Vector3(f[0]-(b[0]+b[2])/2,f[1]-(b[1]+b[3])/2,CINEMA_MESH.dimensions.platform_cm).applyMatrix4(root.matrixWorld).project(camera);const note=document.querySelector('#dimension-note');note.style.left=`${Math.min(76,Math.max(10,(v.x+1)*50+6))}%`;note.style.top=`${Math.min(70,Math.max(16,(1-v.y)*50-7))}%`;}
}
function update(t){caption(t);set(slides[current],'--scan',(t%motion(.85))/motion(.85));if(current===1){set(slides[1],'--reveal',fast(t/motion(.45)));slides[1].querySelectorAll('.task-list>div').forEach((el,i)=>set(el,'--task-opacity',.25+.75*fast((t-1-i*.35)/motion(.25))));}
if(current===2){set(slides[2],'--data-model',renderer?fast((t-7.7)/motion(.5)):0);slides[2].querySelectorAll('.sources a').forEach((el,i)=>set(el,'--source-opacity',.15+.85*fast((t-2.5-i*1.3)/motion(.28))));const svg=slides[2].querySelector('svg');if(playing||!started)svg.unpauseAnimations();else svg.pauseAnimations();}
if(current===5){set(slides[5],'--code',fast(t/motion(.5)));set(slides[5],'--film',fast((t-3)/motion(.35)));set(slides[5],'--ending',fast((t-7.7)/motion(.5)));set(slides[5],'--ending-model',renderer?fast((t-12)/motion(.5)):0);}
if(renderer)renderScene(t);else{if(current===3)show('.scene-visual',t<coastAt?'blender-visual':t<baseAt?'coast-visual':'base-visual');if(current===4)show('.parts-visual,.print-visual,.file-stage',t<sampleAt?'parts-visual':t<filesAt?'print-visual':'file-visual');}
}
function finish(){playing=false;ended=true;audio.pause();stage.classList.remove('playing');stage.classList.add('ended');button.hidden=false;button.innerHTML='<span>↻</span> 再看一遍';}
function drawFrame(){if(renderer&&renderHost){const render=current===0||current===2&&elapsed>6.7||current===3&&document.querySelector('#terrain-visual').classList.contains('shown')||current===4&&elapsed<sampleAt||current===5&&elapsed>11;renderer.domElement.style.visibility=render?'visible':'hidden';if(render)renderer.render(scene,camera);}}
function frame(now){const dt=Math.min((now-last)/1000,.1);last=now;idle+=dt;if(playing){elapsed=Math.max(0,audio.currentTime-offsets[current]);if(current+1<data.length&&elapsed>=data[current].duration){go(current+1,false);elapsed=Math.max(0,audio.currentTime-offsets[current]);}}update(started?elapsed:0);drawFrame();requestAnimationFrame(frame);}
images(0);update(0);if(!exportMode)requestAnimationFrame(frame);
window.STORY={get current(){return current},get playing(){return playing},get audioTime(){return Math.max(0,audio.currentTime-offsets[current])},get elapsed(){return elapsed},get modelReady(){return !!renderer},get ended(){return ended},get shot(){return shot},get growth(){return grow},get baseSplit(){return split},get recessSink(){return sink},go,total,slideCount:data.length};
if(exportMode){
 const style=document.createElement('style');style.textContent='*,*::before,*::after{transition:none!important}#play,#audio-notice{display:none!important}';document.head.appendChild(style);
 let ready=false;
 window.STORY_EXPORT={
  async prepare(){
   playing=false;started=true;audio.pause();button.hidden=true;stage.classList.add('playing');
   for(let i=0;i<slides.length;i++)images(i);
   await document.fonts.ready;
   await Promise.all([...document.images].map(img=>img.decode()));
   if(!await prepareModel()||!await insetTextureReady)throw new Error('视频导出需要完整三维模型与南海纹理');
   for(const svg of document.querySelectorAll('svg'))svg.pauseAnimations();
   ready=true;this.renderAt(0);
   return {duration:total,chapters:data.map((d,i)=>({index:i,start:offsets[i],duration:d.duration})),motionScale:MOTION_SCALE};
  },
  renderAt(seconds){
   if(!ready)throw new Error('先调用 STORY_EXPORT.prepare()');
   if(!Number.isFinite(seconds)||seconds<0)throw new Error('无效帧时间');
   const time=Math.min(seconds,total-1e-6);let i=data.length-1;while(i>0&&time<offsets[i])i--;
   if(current!==i)go(i,false);elapsed=time-offsets[i];update(elapsed);
   for(const svg of document.querySelectorAll('svg')){svg.pauseAnimations();svg.setCurrentTime(elapsed);}
   for(const animation of document.getAnimations()){animation.pause();animation.currentTime=elapsed*1000;}
   drawFrame();
   return {time,chapter:current+1,localTime:elapsed,shot,caption:slides[current].querySelector('.subtitle').textContent,growth:grow,split,sink};
  }
 };
}
