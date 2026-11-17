/* Deterministic frame export. Invoked by export_video.py; frames flow directly to FFmpeg. */
const fs=require('fs'),fsp=fs.promises,path=require('path'),http=require('http'),crypto=require('crypto');
const {spawn,execFileSync}=require('child_process');const {once}=require('events');
async function main(){
 const config=JSON.parse(fs.readFileSync(0,'utf8'));
 let chromium;try{({chromium}=require(config.playwright));}catch(e){throw new Error('Playwright is missing. Install it with npm install playwright, or pass --playwright /package/path. '+e.message);}
 const root=path.resolve(config.root),out=path.resolve(config.output),partial=out.replace(/\.mp4$/i,'')+'.rendering.mp4';
 if(!out.toLowerCase().endsWith('.mp4'))throw new Error('Output must end in .mp4');
 if(fs.existsSync(out)&&!config.overwrite)throw new Error('Output exists; use --overwrite to replace it: '+out);
 await fsp.mkdir(path.dirname(out),{recursive:true});
 const mime={'.html':'text/html','.js':'application/javascript','.css':'text/css','.svg':'image/svg+xml','.webp':'image/webp','.png':'image/png','.mp3':'audio/mpeg'};
 const server=http.createServer(async(req,res)=>{
  try{if(!['GET','HEAD'].includes(req.method)){res.writeHead(405).end();return;}
   const pathname=decodeURIComponent(new URL(req.url,'http://localhost').pathname),file=path.resolve(root,'.'+(pathname==='/'?'/index.html':pathname));
   if(!file.startsWith(root+path.sep)){res.writeHead(403).end();return;}
   const stat=await fsp.stat(file);if(!stat.isFile()){res.writeHead(404).end();return;}
   res.writeHead(200,{'Content-Type':mime[path.extname(file)]||'application/octet-stream','Content-Length':stat.size,'Cache-Control':'no-store'});
   if(req.method==='HEAD')res.end();else fs.createReadStream(file).pipe(res);
  }catch{res.writeHead(404).end();}
 });
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 let browser,encoder,encoderResult,encoderLog='',complete=false;const errors=[],requests=[],samples=[];
 const wallStart=Date.now();let interrupted=false;
 const interrupt=()=>{interrupted=true;if(encoder&&encoder.exitCode===null)encoder.kill('SIGTERM');if(browser)browser.close().catch(()=>{});};
 process.once('SIGINT',interrupt);process.once('SIGTERM',interrupt);
 try{
  browser=await chromium.launch({headless:true,executablePath:config.chromium||undefined});
  const page=await browser.newPage({viewport:{width:config.width,height:config.height},deviceScaleFactor:1});
  page.on('pageerror',e=>errors.push(e.message));page.on('response',r=>{if(r.status()>=400)errors.push(r.status()+' '+r.url());});page.on('request',r=>requests.push(r.url()));
  await page.goto(`http://127.0.0.1:${server.address().port}/index.html?export=1`);
  const metadata=await page.evaluate(()=>STORY_EXPORT.prepare());
  const duration=Math.min(config.duration??metadata.duration-config.start,metadata.duration-config.start);
  if(duration<=0)throw new Error('Start is beyond the narration timeline');
  const frames=Math.ceil(duration*config.fps),encodedDuration=frames/config.fps;
  const cdp=await page.context().newCDPSession(page);
  async function capture(){const r=await cdp.send('Page.captureScreenshot',{format:'png',fromSurface:true,captureBeyondViewport:false,optimizeForSpeed:true});return Buffer.from(r.data,'base64');}
  // Seeking must produce the same frame regardless of previous chapter or wall-clock delay.
  const checkAt=Math.min(metadata.duration-.1,metadata.chapters[3].start+5.4);
  const firstState=await page.evaluate(t=>STORY_EXPORT.renderAt(t),checkAt);const first=await capture();
  await page.evaluate(t=>STORY_EXPORT.renderAt(t),metadata.chapters[4].start+3);
  const secondState=await page.evaluate(t=>STORY_EXPORT.renderAt(t),checkAt);const second=await capture();
  const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
  let pixelDifference={differentPixels:0,maxChannelDelta:0};
  if(hash(first)!==hash(second)){
   const decode=b=>execFileSync(config.ffmpeg,['-v','error','-i','pipe:0','-frames:v','1','-f','rawvideo','-pix_fmt','rgb24','pipe:1'],{input:b,maxBuffer:config.width*config.height*3+1024});
   const a=decode(first),b=decode(second);if(a.length!==b.length)throw new Error('Seek frame dimensions differ');
   for(let n=0;n<a.length;n+=3){const delta=Math.max(Math.abs(a[n]-b[n]),Math.abs(a[n+1]-b[n+1]),Math.abs(a[n+2]-b[n+2]));if(delta)pixelDifference.differentPixels++;pixelDifference.maxChannelDelta=Math.max(pixelDifference.maxChannelDelta,delta);}
  }
  // GPU compositing can round a few border-antialias pixels by 1–3 levels.
  if(JSON.stringify(firstState)!==JSON.stringify(secondState)||pixelDifference.maxChannelDelta>3||pixelDifference.differentPixels>config.width*config.height*.00001){
   await fsp.writeFile(out+'.seek-before.png',first);await fsp.writeFile(out+'.seek-after.png',second);throw new Error('Frame seek is not deterministic: '+JSON.stringify(pixelDifference));
  }
  await page.evaluate(t=>STORY_EXPORT.renderAt(t),Math.min(config.start+2,config.start+duration-.01));
  const cover=out.replace(/\.mp4$/i,'.cover.png');await fsp.writeFile(cover,await capture());
  const args=['-hide_banner','-loglevel','warning','-y','-f','image2pipe','-framerate',String(config.fps),'-vcodec','png','-i','pipe:0',
   '-ss',String(config.start),'-i',path.join(root,'narration.mp3'),'-map','0:v:0','-map','1:a:0','-c:v','libx264','-preset','medium','-crf','18',
   '-vf','scale=iw:ih:in_range=full:out_range=tv:out_color_matrix=bt709,format=yuv420p','-color_primaries','bt709','-color_trc','bt709','-colorspace','bt709','-color_range','tv',
   '-c:a','aac','-b:a','160k','-t',String(encodedDuration),'-movflags','+faststart',partial];
  encoder=spawn(config.ffmpeg,args,{stdio:['pipe','ignore','pipe']});
  encoder.stderr.on('data',b=>{encoderLog=(encoderLog+b.toString()).slice(-12000);});
  encoderResult=new Promise((resolve,reject)=>{encoder.on('error',reject);encoder.on('close',code=>resolve(code));});
  encoder.stdin.on('error',()=>{});
  console.log(`EXPORT ${config.width}x${config.height} ${config.fps}fps · ${frames} frames · ${duration.toFixed(3)}s`);
  for(let n=0;n<frames;n++){
   if(interrupted)throw new Error('Video export interrupted');
   const time=Math.min(config.start+n/config.fps,metadata.duration-1e-6),state=await page.evaluate(t=>STORY_EXPORT.renderAt(t),time);
   const image=await capture();
   if(encoder.exitCode!==null)throw new Error('FFmpeg ended early: '+encoderLog);
   if(!encoder.stdin.write(image))await Promise.race([once(encoder.stdin,'drain'),encoderResult.then(code=>{throw new Error('FFmpeg ended: '+code+' '+encoderLog);})]);
   if(n%config.fps===0||n===frames-1){samples.push({...state,frame:n,sha256:hash(image)});}
   if(n%(config.fps*2)===0||n===frames-1){console.log(`FRAME ${n+1}/${frames} · ${(100*(n+1)/frames).toFixed(1)}% · ${(Date.now()-wallStart)/1000|0}s elapsed`);}
  }
  encoder.stdin.end();const exit=await encoderResult;if(exit!==0)throw new Error('FFmpeg failed: '+encoderLog);
  if(errors.length)throw new Error('Browser asset/render errors: '+errors.join('\n'));
  const probe=JSON.parse(execFileSync(config.ffprobe,['-v','error','-show_streams','-show_format','-count_frames','-of','json',partial],{encoding:'utf8'}));
  const video=probe.streams.find(s=>s.codec_type==='video'),audio=probe.streams.find(s=>s.codec_type==='audio');
  if(!video||!audio||video.width!==config.width||video.height!==config.height||Number(video.nb_read_frames)!==frames||video.codec_name!=='h264'||audio.codec_name!=='aac')throw new Error('MP4 stream/frame verification failed');
  if(Math.abs(Number(probe.format.duration)-encodedDuration)>.15)throw new Error('MP4 duration differs from timeline');
  const report={output:out,cover,width:config.width,height:config.height,fps:config.fps,frames,timelineStart:config.start,timelineDuration:duration,encodedDuration,
   source:metadata,deterministicSeek:true,seekPixelDifference:pixelDifference,deterministicFrameSha256:hash(first),browserErrors:errors,initialAudioRequests:requests.filter(s=>s.endsWith('.mp3')).length,
   wallSeconds:(Date.now()-wallStart)/1000,bytes:fs.statSync(partial).size,streams:probe.streams.map(s=>({codec:s.codec_name,type:s.codec_type,width:s.width,height:s.height,frames:s.nb_read_frames,duration:s.duration})),samples};
  await fsp.rename(partial,out);complete=true;await fsp.writeFile(out.replace(/\.mp4$/i,'.export.json'),JSON.stringify(report,null,2)+'\n');
  console.log('DONE '+out);console.log('REPORT '+out.replace(/\.mp4$/i,'.export.json'));
 }finally{
  process.removeListener('SIGINT',interrupt);process.removeListener('SIGTERM',interrupt);
  if(encoder&&encoder.exitCode===null){encoder.kill('SIGTERM');await encoderResult.catch(()=>{});}
  if(browser)await browser.close();await new Promise(resolve=>server.close(resolve));
  if(!complete)await fsp.rm(partial,{force:true});
 }
}
main().catch(e=>{console.error(e.stack||e);process.exitCode=1;});
