"""Apply derived printing palette to an assembled copy, without changing geometry."""
from pathlib import Path
import json,bpy,numpy as np
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output';PRINT=OUT/'printing'
config=json.loads((ROOT/'model.json').read_text());manifest=json.loads((PRINT/'print_manifest.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(OUT/config['nodes'][-1]['params']['blend_name']))
allowed={n['name'] for n in config['nodes'] if n.get('params',{}).get('group') in ['terrain','terrain_assembly','tray']}
for obj in list(bpy.data.objects):
    if obj.type=='MESH' and obj.name not in allowed:bpy.data.objects.remove(obj,do_unlink=True)
materials={}
for color in config['printing']['colors']:
    m=bpy.data.materials.new(color['name']);h=color['hex'].lstrip('#');m.diffuse_color=tuple(int(h[i:i+2],16)/255 for i in (0,2,4))+(1,);materials[color['id']]=m
for obj in bpy.data.objects:
    if obj.type!='MESH':continue
    color=1
    if obj.name.startswith('P'):
        code=obj.name[1:];color=manifest['province_colors'][code]['filament_id']
    obj.data.materials.clear();obj.data.materials.append(materials[color]);obj.color=materials[color].diffuse_color
for name,base in {**manifest['multicolor_bases'],**manifest.get('multicolor_assemblies',{})}.items():
    old=bpy.data.objects.get(name);bpy.data.objects.remove(old,do_unlink=True)
    for part in base['parts']:
        data=np.load(PRINT/(part['name']+'.npz'));mesh=bpy.data.meshes.new(part['name']);mesh.from_pydata((data['vertices']*.001).tolist(),[],data['faces'].tolist());mesh.update()
        obj=bpy.data.objects.new(part['name'],mesh);bpy.context.collection.objects.link(obj);obj.location=data['assembly_offset_mm']*.001;obj.data.materials.append(materials[part['color']]);obj.color=materials[part['color']].diffuse_color
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':area.spaces.active.shading.color_type='MATERIAL'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/(Path(config['nodes'][-1]['params']['blend_name']).stem+'_multicolor.blend')))
print('Saved assembled printing-color copy',len([o for o in bpy.data.objects if o.type=='MESH']),'meshes')
