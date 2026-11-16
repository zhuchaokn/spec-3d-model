"""Extract cinematic display copies. Never writes model.json or printable geometry."""
from pathlib import Path
import json,re
import numpy as np
import trimesh,shapely,shapely.ops
from shapely.geometry import shape
P=Path(__file__).resolve().parents[1];A=P/'story/assets'
manifest=json.loads((P/'output/printing/print_manifest.json').read_text());model=json.loads((P/'model.json').read_text());report=json.loads((P/'spec/data_report.json').read_text())
palette={p['id']:p['hex'] for p in manifest['palette']}
raw=(A/'motion-mesh.js').read_text();source=json.loads(raw[raw.index('=')+1:].rstrip(';'))
overlap_checks=[]
out={'bounds':report['tray_bounds_cm'],'dimensions':{'slot_depth_cm':model['constants']['SLOT_DEPTH'],'floor_cm':model['constants']['TRAY_FLOOR'],'platform_cm':model['constants']['TRAY_FLOOR']+model['constants']['SLOT_DEPTH'],'vertical_exaggeration':model['constants']['VERTICAL_EXAGGERATION']},'meshes':[]}
for m in source['meshes']:out['meshes'].append({**m,'kind':'province','tile':None})
# Build lightweight layered display solids from the source footprints, avoiding
# aggressive 3D decimation of thin surfaces (which barely reduces those meshes).
floor=out['dimensions']['floor_cm'];depth=out['dimensions']['slot_depth_cm'];top=floor+depth
recess=shape(json.loads((P/'data/processed/national_recess.geojson').read_text())['geometry'])
ocean=shape(json.loads((P/'data/processed/true_ocean_mask.geojson').read_text())['geometry']).difference(recess)
fixed=shapely.union_all([shape(f['geometry']) for f in json.loads((P/'data/processed/fixed_details.geojson').read_text())['features']])
x0,y0,x1,y1=out['bounds'];frame_width=model['constants']['TRAY_FRAME_WIDTH']
frame=shapely.geometry.box(x0,y0,x1,y1).difference(shapely.geometry.box(x0+frame_width,y0+frame_width,x1-frame_width,y1-frame_width))
def solid(g,z0,z1):
 g=shapely.orient_polygons(g);v=[];f=[];idx={}
 def vertex(xy,z):
  key=tuple(round(n,4) for n in (*xy,z))
  if key not in idx:idx[key]=len(v);v.append(key)
  return idx[key]
 polys=[g] if g.geom_type=='Polygon' else list(g.geoms)
 for poly in polys:
  if poly.is_empty or poly.geom_type!='Polygon':continue
  for tri in shapely.constrained_delaunay_triangles(poly).geoms:
   ring=list(tri.exterior.coords)[:3]
   if not shapely.is_ccw(tri.exterior):ring.reverse()
   f.extend([[vertex(p,z1) for p in ring],[vertex(p,z0) for p in ring[::-1]]])
  for ring in [poly.exterior,*poly.interiors]:
   points=list(ring.coords)
   for a,b in zip(points,points[1:]):
    lo1,lo2=vertex(a,z0),vertex(b,z0);hi1,hi2=vertex(a,z1),vertex(b,z1)
    f.extend([[lo1,lo2,hi2],[lo1,hi2,hi1]])
 return v,np.asarray(f).flatten().tolist()
# Simplify shared masks BEFORE taking complementary differences, so coastline
# vertices stay identical on both materials. Never stack equal-height sea/land caps.
ocean=shapely.set_precision(ocean.simplify(.012,preserve_topology=True),.0001)
recess=shapely.set_precision(recess.simplify(.012,preserve_topology=True),.0001)
fixed=shapely.set_precision(fixed.simplify(.012,preserve_topology=True),.0001)
for tray,info in manifest['multicolor_bases'].items():
 part=next(p for p in info['parts'] if '灰色结构' in p['name']);d=np.load(P/'output/printing'/f"{part['name']}.npz")
 vertices=(d['vertices']+d['assembly_offset_mm'])/10;faces=d['faces'];bottom=faces[np.all(np.isclose(vertices[faces,2],0,atol=1e-6),axis=1)]
 footprint=shapely.union_all([shapely.geometry.Polygon(vertices[t,:2]) for t in bottom]).buffer(0)
 footprint=shapely.set_precision(footprint.simplify(.012,preserve_topology=True),.0001)
 sea=footprint.intersection(ocean).difference(frame).difference(fixed)
 # Display-only 3 micron shore clearance survives vertex quantization.
 # This prevents tiny cap overlaps introduced by rounded intersections.
 platform=footprint.difference(recess).difference(sea.buffer(.0003))
 overlap=platform.intersection(sea).area
 assert overlap<1e-8, (tray,overlap)
 overlap_checks.append({'tile':tray,'sea_land_top_overlap_cm2':overlap,'sea_area_cm2':sea.area})
 for name,kind,g,z0,z1,color in [('floor','base',footprint,0,floor,palette[1]),('platform','base',platform,floor,top,palette[1]),('sea_substrate','base',sea,floor,top-.04,palette[1]),('frame','base',footprint.intersection(frame),top,top+model['constants']['TRAY_FRAME_RISE'],palette[1]),('sea','sea',sea,top-.04,top,palette[2]),('fixed','base',footprint.intersection(fixed),floor,top+.08,palette[1])]:
  v,f=solid(g,z0,z1)
  if v:out['meshes'].append(dict(name=tray+'_'+name,kind=kind,tile=tray,vertices=v,indices=f,color=color,center=np.mean(v,axis=0).tolist()))
# Keep fixed Hong Kong / Macao terrain in the display base as well.
for node in model['nodes']:
 if node.get('params',{}).get('code') in [810000,820000,'810000','820000']:
  d=np.load(P/node['params']['mesh_file']);mesh=trimesh.Trimesh(d['vertices']+np.array(node['offset']),d['faces'],process=False)
  if len(mesh.faces)>600:mesh=mesh.simplify_quadric_decimation(face_count=600,aggression=7)
  out['meshes'].append(dict(name=node['name'],kind='base',tile='Tray_X2_Y1',vertices=np.round(mesh.vertices,4).tolist(),indices=mesh.faces.flatten().tolist(),color=palette[1],center=mesh.bounds.mean(0).tolist()))
# An exact-depth temporary fill demonstrates a shared national-outline recess.
# The real printed base is already recessed; only this display lid moves down into the floor.
g=shapely.orient_polygons(shape(json.loads((P/'data/processed/national_recess.geojson').read_text())['geometry']).simplify(.012,preserve_topology=True))
floor=out['dimensions']['floor_cm'];depth=out['dimensions']['slot_depth_cm'];top=floor+depth
vertices=[];faces=[]
for poly in g.geoms:
 verts=[];idx={};ff=[]
 def vertex(xy,z):
  key=tuple(round(v,5) for v in (*xy,z))
  if key not in idx:idx[key]=len(verts);verts.append(key)
  return idx[key]
 for tri in shapely.constrained_delaunay_triangles(poly).geoms:
  ring=list(tri.exterior.coords)[:3]
  if not shapely.is_ccw(tri.exterior):ring.reverse()
  cap_top=[vertex(x,top) for x in ring];cap_bottom=[vertex(x,floor) for x in ring]
  ff.extend([cap_top,cap_bottom[::-1]])
 for ring in [poly.exterior,*poly.interiors]:
  points=list(ring.coords)
  for a,b in zip(points,points[1:]):
   lo1,lo2=vertex(a,floor),vertex(b,floor);hi1,hi2=vertex(a,top),vertex(b,top)
   ff.extend([[lo1,lo2,hi2],[lo1,hi2,hi1]])
 offset=len(vertices);vertices.extend(verts);faces.extend([[v+offset for v in f] for f in ff])
out['meshes'].append(dict(name='National_recess_display_lid',kind='lid',tile=None,vertices=vertices,indices=np.array(faces).flatten().tolist(),color=palette[1],center=[0,0,floor+depth/2]))
# Find a real national coastline point near Shandong for the close-up and 2mm callout.
province=shape(json.loads((P/'data/processed/outline_370000.geojson').read_text())['geometry'])
pt=shapely.ops.nearest_points(g.boundary,province.centroid)[0]
out['recessFocus']=[round(pt.x,4),round(pt.y,4)]
out['macroFocus']=[-9,23.5,1.8]
out['insetBounds']=report['inset']['panel_bounds_cm'];out['insetSourceComponents']=report['inset']['source_component_count']
(A/'cinema-mesh.js').write_text('window.CINEMA_MESH='+json.dumps(out,ensure_ascii=False,separators=(',',':'))+';')
# SVG texture preserves every source island and dash contour.
s=(A/'inset.svg').read_text().replace('<svg ','<svg width="384" height="576" ',1)
(A/'cinema-inset.svg').write_text(s)
proof={'display_mesh_count':len(out['meshes']),'province_count':sum(m['kind']=='province' for m in out['meshes']),'tile_ids':list(manifest['multicolor_bases']),'recess_depth_cm':out['dimensions']['slot_depth_cm'],'display_lid_z_range_cm':[floor,top],'inset_source_components':out['insetSourceComponents'],'bytes':(A/'cinema-mesh.js').stat().st_size,'original_print_files_modified':False,'sea_land_overlap_checks':overlap_checks}
(P/'story/cinematic_geometry.json').write_text(json.dumps(proof,indent=2)+'\n')
print(proof)
