"""Create mechanically continuous multi-color groups with original relief tops."""
import json
import numpy as np,trimesh
from manifold3d import Manifold,Mesh64
from scipy.spatial import cKDTree
from shapely.geometry import shape
from shapely.ops import unary_union
import prepare_print as p


def boolean64(meshes,operation):
    solids=[Manifold(Mesh64(vert_properties=np.asarray(m.vertices,dtype=np.float64),tri_verts=np.asarray(m.faces,dtype=np.uint64))) for m in meshes]
    result=solids[0]
    for solid in solids[1:]:result=(result^solid) if operation=='intersection' else (result+solid)
    data=result.to_mesh64()
    mesh=trimesh.Trimesh(vertices=data.vert_properties[:,:3],faces=data.tri_verts,process=True)
    return mesh


def main():
    config=json.loads((p.ROOT/'model.json').read_text());pr=config['printing'];report=json.loads((p.ROOT/'spec/data_report.json').read_text());manifest=json.loads((p.OUT/'print_manifest.json').read_text())
    source={n['params']['code']:n for n in config['nodes'] if n.get('params',{}).get('group')=='terrain'}
    features=json.loads((p.ROOT/'data/processed/province_print_outlines.geojson').read_text())['features']
    outlines={int(f['properties']['code']):shape(f['geometry']) for f in features if f['properties']['role']=='removable_card'}
    nodes=[];results=[];colored={};removed=set()
    for group in pr['province_assemblies']:
        codes=group['codes'];removed.update(source[code]['name'] for code in codes)
        regions=[outlines[code] for code in codes]
        if group.get('exclave_geometry_file'):
            extra=json.loads((p.ROOT/group['exclave_geometry_file']).read_text())
            regions.extend(shape(f['geometry']) for f in extra['features'])
        geom=unary_union(regions);assert geom.geom_type=='Polygon' and geom.is_valid
        originals={code:p.mesh_for(source[code]) for code in codes};lo=min(m.bounds[0,2] for m in originals.values());cut=lo+group['common_base_thickness_mm']
        base=p.prism(geom,lo/10,cut/10);base.vertices*=10
        base.vertices[np.isclose(base.vertices[:,2],cut,atol=1e-10),2]=cut
        parts=[(group['name']+'_共用底层',group['base_filament_id'],base)];errors={}
        for code,original in originals.items():
            a,b=original.bounds;box=trimesh.creation.box(extents=[b[0]-a[0]+2,b[1]-a[1]+2,b[2]-cut+2]);box.apply_translation([(a[0]+b[0])/2,(a[1]+b[1])/2,(cut+b[2]+2)/2])
            upper=boolean64([original,box],'intersection')
            upper.vertices[np.isclose(upper.vertices[:,2],cut,atol=1e-10),2]=cut
            assert upper.is_watertight and upper.is_winding_consistent and upper.volume>0
            top=original.vertices[original.vertices[:,2]>cut+.001];error=float(cKDTree(upper.vertices).query(top)[0].max());assert error<.001
            errors[str(code)]=error
            parts.append((group['name']+'_'+source[code]['name'],pr['province_color_assignments'][str(code)],upper))
        # Positive overlap with the original lower solids avoids unstable
        # Boolean contact at the color-layer interface. Color parts partition
        # this same finished solid at the exact shared Z plane.
        combined=trimesh.boolean.union([base,*originals.values()],engine='manifold')
        combined.merge_vertices(digits_vertex=6)
        combined.update_faces(combined.nondegenerate_faces(height=0))
        # Regularize only zero-volume internal contact sheets. A retained
        # component must independently be closed; never fill missing faces.
        components=combined.split(only_watertight=False)
        discarded=[m for m in components if abs(m.volume)<=1e-6]
        components=[m for m in components if abs(m.volume)>1e-6]
        assert len(components)==1
        combined=components[0]
        assert combined.is_watertight and combined.is_winding_consistent and combined.body_count==1
        assert abs(sum(m.volume for _,_,m in parts)-combined.volume)<.05
        offset=np.array([(combined.bounds[0,0]+combined.bounds[1,0])/2,(combined.bounds[0,1]+combined.bounds[1,1])/2,lo])
        partinfo=[]
        for name,color,mesh in parts:
            np.savez_compressed(p.OUT/(name+'.npz'),vertices=mesh.vertices-offset,faces=mesh.faces,assembly_offset_mm=offset)
            local=mesh.copy();local.vertices-=offset;local.export(p.OUT/(name+'.stl'))
            partinfo.append({'name':name,'color':color,'volume_mm3':float(mesh.volume),'watertight':True,'triangles':len(mesh.faces)})
        cm=combined.copy();cm.vertices/=10
        result=p.prepare.store_mesh(group['name'],cm,{'group':'terrain_assembly','assembly_name':group['name'],'codes':codes},np.mean(cm.bounds,axis=0).tolist(),nodes)
        results.append(result);colored[group['name']]={'parts':partinfo,'codes':codes,'common_base_thickness_mm':group['common_base_thickness_mm'],'connected_components':1,'top_vertex_error_mm':errors,'regularized_contact_sheet_volume_mm3':sum(abs(m.volume) for m in discarded)}
        print(group['name'],'one connected body',combined.extents,'max relief deviation mm',max(errors.values()),flush=True)
    config['nodes']=[n for n in config['nodes'][:-1] if n['name'] not in {g['name'] for g in pr['province_assemblies']}]+nodes+[config['nodes'][-1]]
    config['nodes'][-1]['after']=[n['name'] for n in config['nodes'][:-1]]
    exports=config['nodes'][-1]['params'];exports['pieces']={k:v for k,v in exports['pieces'].items() if not set(v).intersection(removed)}
    export_dir=pr.get('dovetail_stl_directory','dovetail_combined')
    for group in pr['province_assemblies']:exports['pieces'][export_dir+'/'+group['name']]=[group['name']]
    exports['pieces']={export_dir+'/'+k.split('/')[-1]:v for k,v in exports['pieces'].items()}
    report['parts']=[r for r in report['parts'] if r['object'] not in removed and r['object'] not in colored]+results
    report['removable_assembly_count']=29;report['physical_mesh_count']=33
    manifest['multicolor_assemblies']=colored
    p.prepare.write_json(p.ROOT/'model.json',config);p.prepare.write_json(p.ROOT/'spec/data_report.json',report);p.prepare.write_json(p.OUT/'print_manifest.json',manifest)
    p.prepare.write_json(p.ROOT/'spec/province_assembly_report.json',colored)

if __name__=='__main__':main()
