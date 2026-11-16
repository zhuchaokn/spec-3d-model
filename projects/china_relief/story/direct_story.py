"""Retiming existing male narration with real viewing pauses; no new spoken copy."""
from pathlib import Path
import json,subprocess,wave
import numpy as np
P=Path(__file__).resolve().parent
source=json.loads((P/'voice_source/story.json').read_text())
def timecode(t):
 ms=round(t*1000);return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}'
# Silence is inserted between sentences, leaving the user's six paragraphs unchanged.
spec=[dict(pauses=[],tail=1.35),dict(pauses=[],tail=1.1),dict(pauses=[],tail=1.8),dict(pauses=[(13.072,4.5),(22.5,1.5),(28.903,2)],tail=2.0),dict(pauses=[(4.725,5.0)],tail=1.5),dict(pauses=[],tail=1.5)]
data=[];srt=[];offset=0;number=1;pcm_pages=[]
for i,(row,plan) in enumerate(zip(source,spec)):
 raw=Path(f'/tmp/china_director_{i}.wav');subprocess.run(['ffmpeg','-v','error','-y','-i',str(P/f'voice_source/{i+1:02}.mp3'),'-ac','1','-ar','24000',str(raw)],check=True)
 with wave.open(str(raw)) as w:rate=w.getframerate();pcm=np.frombuffer(w.readframes(w.getnframes()),dtype='<i2').copy()
 cuts=[]
 for target,pause in plan['pauses']:
  # Choose a quiet 10ms region near the known sentence boundary.
  lo=max(0,int((target-.09)*rate));hi=min(len(pcm)-240,int((target+.09)*rate));candidates=np.arange(lo,hi,24)
  scores=[np.mean(pcm[j:j+240].astype(float)**2) for j in candidates]
  cut=int(candidates[int(np.argmin(scores))]+120);cuts.append((cut/rate,pause))
 chunks=[];last=0
 for t,gap in cuts:
  at=round(t*rate);part=pcm[last:at].copy();fade=min(96,len(part));part[-fade:]=(part[-fade:]*np.linspace(1,0,fade)).astype('<i2');chunks.extend([part,np.zeros(round(gap*rate),dtype='<i2')]);last=at
  fade=min(96,len(pcm)-at);pcm[at:at+fade]=(pcm[at:at+fade]*np.linspace(0,1,fade)).astype('<i2')
 chunks.extend([pcm[last:],np.zeros(round(plan['tail']*rate),dtype='<i2')]);result=np.concatenate(chunks);pcm_pages.append(result)
 def shift(t):return t+sum(gap for cut,gap in cuts if t>=cut)
 cues=[]
 for c in row['cues']:
  cues.append({'start':round(shift(c['start']),3),'end':round(shift(c['end']),3),'text':c['text']})
 for c,nxt in zip(cues,cues[1:]):c['end']=min(c['end'],nxt['start'])
 pauses=[];added=0
 for cut,gap in cuts:pauses.append(dict(start=round(cut+added,3),end=round(cut+added+gap,3)));added+=gap
 outwav=Path(f'/tmp/china_director_final_{i}.wav')
 with wave.open(str(outwav),'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(rate);w.writeframes(result.tobytes())
 out=P/f'assets/audio/{i+1:02}.mp3';subprocess.run(['ffmpeg','-v','error','-y','-i',str(outwav),'-ac','1','-ar','24000','-b:a','32k',str(out)],check=True)
 duration=len(result)/rate
 data.append({**row,'audio_duration':round(duration,3),'duration':round(duration+.08,3),'audio_bytes':out.stat().st_size,'cues':cues,'viewing_pauses':pauses})
 for c in cues:
  srt.append(f'{number}\n{timecode(offset+c["start"])} --> {timecode(offset+c["end"])}\n{c["text"]}\n');number+=1
 offset+=duration+.08
 print(i+1,round(duration,2),pauses,flush=True)
def encode(samples,out):
 path=Path('/tmp/china_director_join.wav')
 with wave.open(str(path),'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(24000);w.writeframes(np.concatenate(samples).tobytes())
 subprocess.run(['ffmpeg','-v','error','-y','-i',str(path),'-b:a','32k',str(out)],check=True)
# Match exported audio precisely to per-page transition pads.
full=[np.concatenate([x,np.zeros(1920,dtype='<i2')]) for x in pcm_pages];encode(full,P/'narration.mp3')
for i in range(3):encode(full[i*2:i*2+2],P/f'assets/audio/batch-{i+1}.mp3')
(P/'story.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n');(P/'story-data.js').write_text('window.STORY_DATA='+json.dumps(data,ensure_ascii=False,separators=(',',':'))+';')
for name in ['captions.srt','captions.srt.txt']:(P/name).write_text('\n'.join(srt))
(P/'narration.txt').write_text('3D 中国地图 / 导演版\n原六段文案 · Yunxi 男声 +18% · 动作之间加入观看停顿\n\n'+'\n\n'.join(f'{i+1:02}\n{x["narration"]}' for i,x in enumerate(data))+'\n')
print('TOTAL',offset)
