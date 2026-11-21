"""Build china_relief through the repository's pure dispatch engine.

blender --background --factory-startup --python run_model.py
or execute_blender_code(file_path=...). Uses a dedicated scene; existing work survives.
"""
import sys
import os
import json
import hashlib
import importlib

PROJ=os.path.dirname(os.path.abspath(__file__))
LIB=os.path.join(os.path.dirname(os.path.dirname(PROJ)),'lib')
if LIB not in sys.path: sys.path.insert(0,LIB)
import s3d,engine
importlib.reload(s3d); importlib.reload(engine)
import bpy
import bmesh

with open(os.path.join(PROJ,'model.json'),encoding='utf-8') as f:
    config=json.load(f)
fingerprint=hashlib.sha256(json.dumps({'constants':config['constants'],'data':config['data']},sort_keys=True).encode()).hexdigest()
if fingerprint!=config.get('prepared_fingerprint') or not config['nodes']:
    raise RuntimeError('model.json changed or data not prepared: run tools/prepare.py first')

old=bpy.data.scenes.get('China Relief')
if old:
    for obj in list(old.objects): bpy.data.objects.remove(obj,do_unlink=True)
    bpy.data.scenes.remove(old)
scene=bpy.data.scenes.new('China Relief')
bpy.context.window.scene=scene
s3d.set_cm_units()
scene['horizontal_scale_denominator']=100/config['constants']['HORIZONTAL_CM_PER_M']
scene['vertical_exaggeration']=config['constants']['VERTICAL_EXAGGERATION']
scene['boundary_limitations']=config['data']['boundary_coordinate_assumption']

# Initial exports occur after the entire mesh build; validate before exporting.
original_nodes=config['nodes']
export_node=original_nodes[-1]
build_config=dict(config,nodes=original_nodes[:-1])
temporary=os.path.join(PROJ,'output','build_registry.json')
os.makedirs(os.path.dirname(temporary),exist_ok=True)
# Engine resolves project-relative mesh paths and ops from the JSON directory.
# Keep the temporary registry beside model.json, then remove it after dispatch.
temporary=os.path.join(PROJ,'build_registry.json')
with open(temporary,'w',encoding='utf-8') as f: json.dump(build_config,f,ensure_ascii=False)
try:
    built=engine.run_model(temporary,lib_dir=LIB)
finally:
    os.remove(temporary)

bpy.context.view_layer.update()
reports=[]
for obj in scene.objects:
    if obj.type!='MESH': continue
    bm=bmesh.new(); bm.from_mesh(obj.data)
    boundary=sum(e.is_boundary for e in bm.edges)
    nonmanifold=sum(not e.is_manifold for e in bm.edges)
    inconsistent=sum(e.is_manifold and not e.is_contiguous for e in bm.edges)
    volume=bm.calc_volume(signed=True)*1e9
    bm.free()
    if boundary or nonmanifold or inconsistent or volume<=0:
        raise RuntimeError(f'Invalid Blender mesh: {obj.name} boundary={boundary}, nonmanifold={nonmanifold}, volume={volume}')
    reports.append({'object':obj.name,'dimensions_mm':[v*1000 for v in obj.dimensions],
                    'boundary_edges':boundary,'nonmanifold_edges':nonmanifold,
                    'inconsistent_edges':inconsistent,'volume_mm3':volume})

for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            space=area.spaces.active
            space.shading.type='SOLID'; space.shading.color_type='OBJECT'
            space.clip_end=100
            from mathutils import Quaternion
            space.region_3d.view_rotation=Quaternion((.9238795,.3826834,0,0))
            space.region_3d.view_distance=.85
            height=max(o.location.y+o.dimensions.y/2 for o in scene.objects)
            space.region_3d.view_location=(0,height/2,0)

export_run=engine._load_op(export_node['op'],[PROJ,LIB])
export_run(engine.Ctx(export_node,(0,0,0),export_node['params'],{},proj_dir=PROJ))
with open(os.path.join(PROJ,'spec','blender_report.json'),'w',encoding='utf-8') as f:
    json.dump({'blender_version':bpy.app.version_string,'mesh_count':len(reports),'parts':reports},f,ensure_ascii=False,indent=2)
print(f'Blender validated {len(reports)} closed manifold meshes; saved output/{export_node["params"]["blend_name"]}',flush=True)
