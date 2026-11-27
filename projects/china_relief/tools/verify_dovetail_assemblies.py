"""Check actual mating geometry, preserved single parts and nine-plate placement."""
import argparse,json,zipfile,xml.etree.ElementTree as ET
import numpy as np,shapely,trimesh
from shapely.geometry import box,Point
from shapely.ops import unary_union
import prepare_print as p
from revise_nine_plate_project import C,P,metadata
from verify_3mf_meshes import verify


def transformed(v,t):
    a=np.array([float(x) for x in (t or '1 0 0 0 1 0 0 0 1 0 0 0').split()])
    m=a[:9].reshape(3,3)
    result=v[:,0,None]*m[0]+v[:,1,None]*m[1]+v[:,2,None]*m[2]+a[9:]
    assert np.isfinite(result).all()
    return result


def main():
    ap=argparse.ArgumentParser();ap.add_argument('previous');ap.add_argument('revised');args=ap.parse_args()
    config=json.loads((p.ROOT/'model.json').read_text());c=config['constants'];pr=config['printing']
    report=json.loads((p.ROOT/'spec/data_report.json').read_text());manifest=json.loads((p.OUT/'print_manifest.json').read_text())
    x0,y0,x1,y1=report['tray_bounds_cm'];xs=np.linspace(x0,x1,3);ys=np.linspace(y0,y1,3);outlines={};bases=[]
    for n in config['nodes']:
        if n.get('params',{}).get('group')!='tray':continue
        ix,iy=np.array(n['params']['tile'])-1
        geom=p.prepare.tray_polygon(box(xs[ix],ys[iy],xs[ix+1],ys[iy+1]),ix,iy,2,2,c);outlines[ix,iy]=geom
        mesh=p.mesh_for(n);tri=mesh.triangles;bottom=tri[np.all(np.isclose(tri[:,:,2],0,atol=1e-7),axis=1)]
        footprint=unary_union(shapely.polygons(bottom[:,:,:2]))
        expected=shapely.affinity.scale(geom,10,10,origin=(0,0))
        assert footprint.symmetric_difference(expected).area<.001
        assert mesh.is_watertight and mesh.body_count==1 and max(mesh.extents)<256
        bases.append({'name':n['name'],'dimensions_mm':mesh.extents.tolist(),'actual_bottom_matches_outline':True})
    joints=[];w=c['TRAY_TAB_WIDTH'];h=c['TRAY_TAB_HEAD_WIDTH'];length=c['TRAY_TAB_LENGTH'];clear=c['TRAY_TAB_CLEARANCE']
    assert h>w+2*clear and np.isclose(clear*10,.2) and np.isclose(c['TRAY_SEAM_GAP']*10,.1)
    for vertical in [False,True]:
        for row in [0,1]:
            male=outlines[(row,0) if vertical else (0,row)]
            female=outlines[(row,1) if vertical else (1,row)]
            for fraction in [1/3,2/3]:
                axis=xs[row]+(xs[row+1]-xs[row])*fraction if vertical else ys[row]+(ys[row+1]-ys[row])*fraction
                def point(u,v):return Point(axis+v,ys[1]+u) if vertical else Point(xs[1]+u,axis+v)
                if c.get('TRAY_PADDLE_ENABLED'):
                    profile=p.prepare.paddle_profile(c,True)
                    coords=np.array(profile.exterior.coords);mid=(coords[:-1]+coords[1:])/2
                    radius=h/2;center=length-radius
                    arc=mid[(mid[:,0]>c['TRAY_PADDLE_BLEND_RADIUS']*3)&(np.abs(np.linalg.norm(mid-[center,0],axis=1)-radius)<.001)]
                    arc=arc[::max(1,len(arc)//24)];assert len(arc)>=12
                    checked=mid[mid[:,0]>c['TRAY_SEAM_GAP']+clear+c['NUMERICAL_GAP']]
                    checked=checked[::max(1,len(checked)//48)]
                    points=[point(u,v) for u,v in checked]
                    assert all(male.boundary.distance(q)<1e-8 for q in points)
                    distances=[female.boundary.distance(q) for q in points]
                else:
                    # Midpoints of both sloping flanks and the dovetail end face.
                    points=[point(length/2,s*(w+h)/4) for s in [-1,1]]+[point(length,0)]
                    distances=[female.boundary.distance(q) for q in points]
                assert np.allclose(distances,clear,atol=1e-8)
                assert all(male.boundary.distance(q)<1e-8 for q in points)
                assert male.intersection(female).area<1e-10
                joints.append({'axis':'Y' if vertical else 'X','row':row,'fraction':fraction,'measured_clearance_mm':[v*10 for v in distances]})
    assembly_checks=[]
    for n in config['nodes']:
        if n.get('params',{}).get('group')!='terrain_assembly':continue
        mesh=p.mesh_for(n);info=manifest['multicolor_assemblies'][n['name']]
        assert mesh.is_watertight and mesh.body_count==1 and mesh.is_winding_consistent
        assert abs(sum(part['volume_mm3'] for part in info['parts'])-mesh.volume)<.05
        assert max(info['top_vertex_error_mm'].values())<.001
        assembly_checks.append({'name':n['name'],'one_connected_closed_solid':True,'shared_bottom_mm':info['common_base_thickness_mm'],'dimensions_mm':mesh.extents.tolist(),'color_volume_delta_mm3':sum(part['volume_mm3'] for part in info['parts'])-mesh.volume,'unchanged_relief_top_error_mm':info['top_vertex_error_mm']})
    merged_codes={str(v) for g in pr['province_assemblies'] for v in g['codes']};preserved=[];plates=[]
    with zipfile.ZipFile(args.previous) as old,zipfile.ZipFile(args.revised) as new:
        core=ET.fromstring(new.read('3D/3dmodel.model'));cfg=ET.fromstring(new.read('Metadata/model_settings.config'));oc={o.get('id'):o for o in cfg.findall('object')};build={i.get('objectid'):i for i in core.findall(C+'build/'+C+'item')}
        oldcfg=ET.fromstring(old.read('Metadata/model_settings.config'));oldcore=ET.fromstring(old.read('3D/3dmodel.model'));oldobj={o.get('id'):o for o in oldcfg.findall('object')}
        models={path:ET.fromstring(new.read(path)) for path in new.namelist() if path.endswith('.model')}
        lookup={(path,o.get('id')):o for path,m in models.items() for o in m.findall(C+'resources/'+C+'object')}
        def vertices(path,oid):
            obj=lookup[path,oid];mesh=obj.find(C+'mesh')
            if mesh is not None:return np.array([[float(v.get(k)) for k in ['x','y','z']] for v in mesh.findall(C+'vertices/'+C+'vertex')])
            return np.vstack([transformed(vertices(comp.get(P+'path',path).lstrip('/'),comp.get('objectid')),comp.get('transform')) for comp in obj.findall(C+'components/'+C+'component')])
        assert len(oc)==len(build)==33
        for oid,obj in oc.items():
            name=metadata(obj)['name'];code=name.split('_')[0]
            if code.isdigit():
                assert code not in merged_codes
                assert ET.tostring(obj)==ET.tostring(oldobj[oid])
                a=next(o for o in oldcore.findall(C+'resources/'+C+'object') if o.get('id')==oid)
                for comp in a.findall(C+'components/'+C+'component'):
                    path=comp.get(P+'path').lstrip('/');assert old.read(path)==new.read(path)
                assert ET.tostring(build[oid])==ET.tostring(next(i for i in oldcore.findall(C+'build/'+C+'item') if i.get('objectid')==oid))
                preserved.append(name)
        assert len(preserved)==27
        for i,plate in enumerate(cfg.findall('plate'),1):
            ids=[metadata(mi)['object_id'] for mi in plate.findall('model_instance')];origin=np.array([0.,0.,0.])
            # Bambu multi-plate coordinates: derive each plate origin from its
            # existing base placement; user plates use a 1.2*bed pitch.
            pitch=c['PRINT_BED']*10*1.2;origin[:2]=[(i-1)%3*pitch,-((i-1)//3)*pitch]
            bounds=[]
            for oid in ids:
                v=transformed(vertices('3D/3dmodel.model',oid),build[oid].get('transform'))-origin
                b=np.array([v.min(axis=0),v.max(axis=0)])
                assert np.isclose(b[0,2],0,atol=1e-5) and b[1,2]<256
                assert np.min(b[0,:2])>=pr['brim_width_mm']-1e-5 and np.max(b[1,:2])<=256-pr['brim_width_mm']+1e-5,(i,b)
                bounds.append(b.tolist())
            plates.append({'plate':i,'objects':[metadata(oc[oid])['name'] for oid in ids],'bounds_mm':bounds})
        assert [len(v['objects']) for v in plates]==[2,1,1,1,1,6,7,7,7]
        settings=json.loads(new.read('Metadata/project_settings.config'))
        assert settings['enable_prime_tower']=='0' and settings['sparse_infill_density']=='5%'
    result={'joint_style':'round_paddle' if c.get('TRAY_PADDLE_ENABLED') else 'dovetail','joint_count':len(joints),'profile_clearance_mm':clear*10,'flat_seam_gap_mm':c['TRAY_SEAM_GAP']*10,'joints':joints,'bases':bases,'assemblies':assembly_checks,'preserved_single_provinces':preserved,'physical_objects':33,'removable_pieces':29,'plate_count':9,'closed_color_meshes':verify(args.revised),'plates':plates}
    p.prepare.write_json(p.ROOT/'spec/dovetail_assembly_verification.json',result)
    label='round paddle joints' if c.get('TRAY_PADDLE_ENABLED') else 'dovetails'
    print(f'Verified 8 {label}, {clear*10:g} mm profiles, 2 connected assemblies, 27 unchanged provinces, 9 plates / 33 objects')

if __name__=='__main__':main()
