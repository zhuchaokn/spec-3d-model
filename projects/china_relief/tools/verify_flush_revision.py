"""Verify actual exported color meshes, source preservation and 9-plate layout."""
import argparse,hashlib,json,zipfile,xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np,shapely,trimesh
from shapely.geometry import shape,box,Point
from shapely.ops import unary_union
import prepare
import prepare_print as pp
from revise_nine_plate_project import C,P,metadata
ROOT=Path(__file__).resolve().parents[1]


def top_region(mesh,level):
    triangles=mesh.triangles;cross=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0])
    mask=np.all(np.isclose(triangles[:,:,2],level,atol=1e-6,rtol=0),axis=1)&(cross[:,2]>0)
    return unary_union(shapely.polygons(triangles[mask,:,:2]))


def main():
    ap=argparse.ArgumentParser();ap.add_argument('source',type=Path);ap.add_argument('revised',type=Path);args=ap.parse_args()
    cfg=json.loads((ROOT/'model.json').read_text());c=cfg['constants'];manifest=json.loads((pp.OUT/'print_manifest.json').read_text());report=json.loads((ROOT/'spec/data_report.json').read_text())
    backup=ROOT/'output/revision_backup/province_hashes.json'
    hashes=json.loads(backup.read_text());unchanged=[]
    for n in cfg['nodes']:
        if n['name'] in hashes:
            assert prepare.sha(ROOT/n['params']['mesh_file'])==hashes[n['name']]
            unchanged.append(n['name'])
    assert len(unchanged)==32
    x0,y0,x1,y1=report['tray_bounds_cm'];xs=np.linspace(x0,x1,3);ys=np.linspace(y0,y1,3);high=(c['TRAY_FLOOR']+c['SLOT_DEPTH'])*10;bottom=high-cfg['printing']['inset_inlay_thickness_mm']
    checks=[]
    for node in cfg['nodes']:
        if node.get('params',{}).get('group')!='tray':continue
        ix,iy=np.array(node['params']['tile'])-1;cell=box(xs[ix],ys[iy],xs[ix+1],ys[iy+1]);outline=prepare.tray_polygon(cell,ix,iy,2,2,c)
        old=prepare.tray_polygon(cell,ix,iy,2,2,dict(c,TRAY_OUTER_CORNER_RADIUS=0));removed=old.difference(outline)
        cx=xs[0] if ix==0 else xs[-1];cy=ys[0] if iy==0 else ys[-1];r=c['TRAY_OUTER_CORNER_RADIUS']
        square=box(min(cx,cx+(r if ix==0 else -r)),min(cy,cy+(r if iy==0 else -r)),max(cx,cx+(r if ix==0 else -r)),max(cy,cy+(r if iy==0 else -r)))
        assert removed.difference(square).area<1e-10
        assert removed.area>0 and not outline.covers(Point(cx,cy))
        meshes={}
        for part in manifest['multicolor_bases'][node['name']]['parts']:
            a=np.load(pp.OUT/(part['name']+'.npz'));mesh=trimesh.Trimesh(vertices=a['vertices']+a['assembly_offset_mm'],faces=a['faces'],process=False)
            assert mesh.is_watertight and mesh.is_winding_consistent and mesh.volume>0
            meshes[part['name']]=mesh
            if part['color']!=cfg['printing']['base_filament_id']:
                assert np.allclose(mesh.bounds[:,2],[bottom,high],atol=1e-7)
        fixed=shape(json.loads((ROOT/'data/processed/fixed_details.geojson').read_text())['features'][0]['geometry']).intersection(outline)
        original=pp.mesh_for(node);actual_top=top_region(original,high)
        assert shapely.affinity.scale(fixed,10,10,origin=(0,0)).difference(actual_top).area<.001
        marks=next((m for n,m in meshes.items() if '岛礁文字' in n),None)
        if marks is not None:
            gray=next(m for n,m in meshes.items() if n.endswith('灰色结构'))
            # Each inlaid footprint rests on gray material at the same interface.
            support=top_region(gray,bottom);footprint=top_region(marks,high)
            assert footprint.difference(support).area<.001
            source=shape(json.loads((ROOT/'data/processed/south_sea_inset.geojson').read_text())['geometry'])
            assert footprint.symmetric_difference(shapely.affinity.scale(source,10,10,origin=(0,0))).area<.001
        checks.append({'object':node['name'],'max_mm':original.extents.tolist(),'removed_corner_area_mm2':removed.area*100,'fixed_details_flush':True,'all_color_meshes_manifold':True,'inlay_supported':True if marks is not None else None,'partition_delta_mm3':manifest['multicolor_bases'][node['name']]['volume_delta_mm3']})
    with zipfile.ZipFile(args.source) as old,zipfile.ZipFile(args.revised) as new:
        a=ET.fromstring(old.read('3D/3dmodel.model'));b=ET.fromstring(new.read('3D/3dmodel.model'));s=ET.fromstring(old.read('Metadata/model_settings.config'));t=ET.fromstring(new.read('Metadata/model_settings.config'))
        assert ET.tostring(a.find(C+'build'))==ET.tostring(b.find(C+'build'))
        assert len(t.findall('plate'))==9
        assert [ET.tostring(p) for p in s.findall('plate')]==[ET.tostring(p) for p in t.findall('plate')]
        assert old.read('Metadata/project_settings.config')==new.read('Metadata/project_settings.config')
        for oc in t.findall('object'):
            name=metadata(oc)['name']
            if name.startswith('Tray_'):continue
            previous=next(o for o in s.findall('object') if o.get('id')==oc.get('id'))
            assert ET.tostring(previous)==ET.tostring(oc)
            obj=next(o for o in a.findall(C+'resources/'+C+'object') if o.get('id')==oc.get('id'))
            for comp in obj.findall(C+'components/'+C+'component'):
                path=comp.get(P+'path').lstrip('/');assert old.read(path)==new.read(path)
        settings=json.loads(new.read('Metadata/project_settings.config'))
        assert settings['enable_prime_tower']=='0' and settings['sparse_infill_density']=='5%' and settings['sparse_infill_pattern']=='gyroid'
    result={'revision':cfg['design_revision'],'unchanged_province_meshes':len(unchanged),'unchanged_plate_layout':True,'plate_count':9,'corner_radius_mm':r*10,'inlay_top_mm':high,'inlay_bottom_mm':bottom,'inlay_layers':cfg['printing']['inset_inlay_thickness_mm']/cfg['printing']['base_layer_height_mm'],'slot_depth_mm':c['SLOT_DEPTH']*10,'slot_clearance_per_side_mm':c['SLOT_CLEARANCE']*10,'bases':checks}
    prepare.write_json(ROOT/'spec/flush_revision_report.json',result);print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
