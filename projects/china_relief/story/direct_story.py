"""Package the original male narration continuously, without inserted viewing silence."""
from pathlib import Path
import json, shutil, subprocess, wave
import numpy as np
P=Path(__file__).resolve().parent
source=json.loads((P/'voice_source/story.json').read_text())
def timecode(t):
 ms=round(t*1000);return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}'
data=[];srt=[];offset=0;number=1;pcm_pages=[]
for i,row in enumerate(source):
 original=P/f'voice_source/{i+1:02}.mp3';out=P/f'assets/audio/{i+1:02}.mp3'
 shutil.copy2(original,out) # No further lossy encoding or sentence edits.
 raw=Path(f'/tmp/china_continuous_{i}.wav')
 subprocess.run(['ffmpeg','-v','error','-y','-i',str(original),'-ac','1','-ar','24000',str(raw)],check=True)
 with wave.open(str(raw)) as w:pcm=np.frombuffer(w.readframes(w.getnframes()),dtype='<i2').copy()
 pcm_pages.append(pcm);duration=len(pcm)/24000
 cues=[dict(c) for c in row['cues']]
 for c,nxt in zip(cues,cues[1:]):c['end']=min(c['end'],nxt['start'])
 data.append({**row,'audio_duration':round(duration,3),'duration':round(duration,3),'audio_bytes':out.stat().st_size,'cues':cues,'viewing_pauses':[]})
 for c in cues:
  srt.append(f'{number}\n{timecode(offset+c["start"])} --> {timecode(offset+c["end"])}\n{c["text"]}\n');number+=1
 offset+=duration
 print(i+1,round(duration,3),flush=True)
def encode(samples,out):
 path=Path('/tmp/china_continuous_join.wav')
 with wave.open(str(path),'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(24000);w.writeframes(np.concatenate(samples).tobytes())
 subprocess.run(['ffmpeg','-v','error','-y','-i',str(path),'-ac','1','-ar','24000','-b:a','32k',str(out)],check=True)
encode(pcm_pages,P/'narration.mp3')
for i in range(3):encode(pcm_pages[i*2:i*2+2],P/f'assets/audio/batch-{i+1}.mp3')
(P/'story.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n');(P/'story-data.js').write_text('window.STORY_DATA='+json.dumps(data,ensure_ascii=False,separators=(',',':'))+';')
for name in ['captions.srt','captions.srt.txt']:(P/name).write_text('\n'.join(srt))
(P/'narration.txt').write_text('3D 中国地图 / 导演版\n原六段文案 · Yunxi 男声 +18% · 连续口播，无额外观看静音\n\n'+'\n\n'.join(f'{i+1:02}\n{x["narration"]}' for i,x in enumerate(data))+'\n')
print('TOTAL',offset)
