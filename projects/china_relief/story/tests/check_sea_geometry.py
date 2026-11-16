"""Check published display caps, after rounding, for the original z-fighting defect."""
import json
from pathlib import Path
import numpy as np
import shapely
from shapely.geometry import Polygon
P=Path(__file__).resolve().parents[1]
s=(P/'assets/cinema-mesh.js').read_text();model=json.loads(s.split('=',1)[1].rstrip(';'))
def cap(mesh,z):
 v=np.asarray(mesh['vertices']);tri=v[np.asarray(mesh['indices']).reshape(-1,3)]
 return shapely.union_all([Polygon(t[:,:2]) for t in tri[np.all(np.isclose(tri[:,:,2],z,atol=1e-7),axis=1)]])
checks=[]
for sea in [m for m in model['meshes'] if m['kind']=='sea']:
 platform=next(m for m in model['meshes'] if m['name']==sea['tile']+'_platform')
 overlap=cap(sea,.4).intersection(cap(platform,.4)).area
 assert overlap<1e-10,(sea['tile'],overlap)
 assert min(v[2] for v in sea['vertices'])==.36
 substrate=next(m for m in model['meshes'] if m['name']==sea['tile']+'_sea_substrate')
 assert max(v[2] for v in substrate['vertices'])==.36
 checks.append({'tile':sea['tile'],'emitted_sea_land_overlap_cm2':overlap})
assert len(checks)==3 # Northwest tile contains no ocean.
source=json.loads((P/'voice_source/story.json').read_text());story=json.loads((P/'story.json').read_text())
for a,b in zip(source,story):
 assert a['narration']==b['narration']
 assert not b['viewing_pauses']
 assert b['duration']==b['audio_duration']
 assert [(c['text'],c['start']) for c in a['cues']]==[(c['text'],c['start']) for c in b['cues']]
print(json.dumps({'caps':checks,'continuous_narration_seconds':sum(d['duration'] for d in story)},indent=2))
