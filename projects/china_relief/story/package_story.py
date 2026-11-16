"""Package only the static story and an offline ZIP, excluding working sources."""
from pathlib import Path
import re,shutil,zipfile
P=Path(__file__).resolve().parent;B=P.parent/'output/story_public'
if B.exists():shutil.rmtree(B)
B.mkdir(parents=True)
files=['index.html','style.css','app.js','story.json','story-data.js','narration.txt','narration.mp3','captions.srt.txt','credits.html']
assets=set(re.findall(r'(?:src|data-src)="(assets/[^" ]+)"',(P/'index.html').read_text()))|{'assets/three.min.js','assets/cinema-mesh.js','assets/cinema-inset.svg','assets/THREE-LICENSE.txt'}
assets|={f'assets/audio/{i:02}.mp3' for i in range(1,7)}|{f'assets/audio/batch-{i}.mp3' for i in range(1,4)}
for name in sorted(set(files)|assets):
 dest=B/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(P/name,dest)
with zipfile.ZipFile(P.parent/'output/china_relief_制作故事_HTML.zip','w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for f in sorted(B.rglob('*')):
  if f.is_file():z.write(f,Path('china_relief_story')/f.relative_to(B))
 for name in ['README.md','captions.srt','cinematic_plan.md']:z.write(P/name,Path('china_relief_story')/name)
print('files',sum(f.is_file() for f in B.rglob('*')),'bytes',sum(f.stat().st_size for f in B.rglob('*') if f.is_file()))
