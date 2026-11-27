"""Verify filled assembly holes and removed base posts using actual meshes."""
import argparse,json,zipfile,xml.etree.ElementTree as ET
import numpy as np,shapely
from shapely.geometry import shape,Polygon
from shapely.ops import unary_union
from scipy.spatial import cKDTree
import prepare_print as p
from revise_nine_plate_project import C,P,metadata
from verify_flush_revision import top_region


def main():
    ap=argparse.ArgumentParser();ap.add_argument('old_project');ap.add_argument('new_project');args=ap.parse_args()
    cfg=json.loads((p.ROOT/'model.json').read_text());c=cfg['constants'];group=next(g for g in cfg['printing']['province_assemblies'] if g.get('exclave_geometry_file'))
    geo=json.loads((p.ROOT/group['exclave_geometry_file']).read_text());region=unary_union([shape(f['geometry']) for f in geo['features']]);region_mm=shapely.affinity.scale(region,10,10,origin=(0,0))
    nodes={n['name']:n for n in cfg['nodes']};mesh=p.mesh_for(nodes[group['name']]);lo=c['TRAY_FLOOR']*10
    assert mesh.is_watertight and mesh.body_count==1 and mesh.euler_number==2
    tris=mesh.triangles[np.all(np.isclose(mesh.triangles[:,:,2],lo,atol=1e-6),axis=1)]
    bottom=unary_union(shapely.polygons(tris[:,:,:2]));assert bottom.geom_type=='Polygon' and not bottom.interiors
    assert region_mm.difference(bottom).area<.001
    manifest=json.loads((p.OUT/'print_manifest.json').read_text());parts=manifest['multicolor_assemblies'][group['name']]['parts']
    for part in parts:
        data=np.load(p.OUT/(part['name']+'.npz'))
        if part['name'].endswith('共用底层'):
            assert np.allclose([data['vertices'][:,2].min(),data['vertices'][:,2].max()],[0,group['common_base_thickness_mm']])
        if part['name'].endswith('P130000'):assert part['color']==cfg['printing']['province_color_assignments']['130000']
    base=p.mesh_for(nodes['Tray_X2_Y2']);floor=top_region(base,lo);platform=top_region(base,lo+c['SLOT_DEPTH']*10)
    assert region_mm.difference(floor).area<.001 and platform.intersection(region_mm).area<.001
    # Existing relief vertices are retained in the restored Hebei source.
    source=p.mesh_for(nodes['P130000']);backup=json.loads((p.ROOT/'output/hebei_exclave_backup/model.json').read_text());oldnode=next(n for n in backup['nodes'] if n['name']=='P130000')
    olddata=np.load(p.ROOT/'output/hebei_exclave_backup/P130000.npz');oldv=(olddata['vertices']+oldnode['offset'])*10
    error=float(cKDTree(source.vertices).query(oldv)[0].max());assert error<.001
    unchanged=[]
    with zipfile.ZipFile(args.old_project) as a,zipfile.ZipFile(args.new_project) as b:
        oldcore=ET.fromstring(a.read('3D/3dmodel.model'));core=ET.fromstring(b.read('3D/3dmodel.model'));oldcfg=ET.fromstring(a.read('Metadata/model_settings.config'));config=ET.fromstring(b.read('Metadata/model_settings.config'))
        assert ET.tostring(oldcore.find(C+'build'))==ET.tostring(core.find(C+'build'))
        assert [ET.tostring(p) for p in oldcfg.findall('plate')]==[ET.tostring(p) for p in config.findall('plate')]
        assert a.read('Metadata/project_settings.config')==b.read('Metadata/project_settings.config')
        roots={o.get('id'):o for o in core.findall(C+'resources/'+C+'object')}
        for obj in config.findall('object'):
            name=metadata(obj)['name']
            if name in [group['name'],'Tray_X2_Y2']:continue
            for comp in roots[obj.get('id')].findall(C+'components/'+C+'component'):
                path=comp.get(P+'path').lstrip('/');assert a.read(path)==b.read(path)
            unchanged.append(name)
    assert len(unchanged)==31
    result={'filled_regions':len(geo['features']),'assembly_bottom_holes':0,'assembly_euler_number':int(mesh.euler_number),'assembly_connected_solids':1,'common_base_mm':group['common_base_thickness_mm'],'enclave_base_floor_mm':lo,'fixed_posts_removed':True,'retained_hebei_vertex_error_mm':error,'unchanged_objects':unchanged,'changed_objects':[group['name'],'Tray_X2_Y2'],'changed_plates':[1,5],'all_original_plate_assignment_preserved':True}
    p.prepare.write_json(p.ROOT/'spec/hebei_exclave_verification.json',result)
    print('Verified zero through-holes, continuous 1.6 mm bottom, 2 mm floor instead of posts; 31 other objects unchanged')

if __name__=='__main__':main()
