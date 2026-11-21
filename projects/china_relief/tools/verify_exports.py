"""Independent STL round-trip checks: finite coordinates, closed topology, units."""
import json
from pathlib import Path
import numpy as np
import trimesh

ROOT=Path(__file__).resolve().parents[1]

def main():
    registry=json.loads((ROOT/'model.json').read_text())
    report=json.loads((ROOT/'spec/data_report.json').read_text())
    nodes={n['name']:n for n in registry['nodes']}
    expected={p['object']:p for p in report['parts']}
    result=[]
    for filename,names in registry['nodes'][-1]['params']['pieces'].items():
        path=ROOT/'output'/(filename+'.stl')
        mesh=trimesh.load_mesh(path,process=True)
        assert np.isfinite(mesh.vertices).all(),path
        assert mesh.is_watertight and mesh.is_winding_consistent and mesh.volume>0,path
        if all(nodes[name]['params']['group']=='tray' for name in names):
            assert mesh.body_count==1,(path,'Fixed terrain must connect to the base')
        # Expected dimensions and volume originate in the independently prepared cm meshes.
        boxes=[]
        for name in names:
            with np.load(ROOT/nodes[name]['params']['mesh_file']) as prepared:
                v=(prepared['vertices']+np.array(nodes[name]['offset']))*10
            boxes.append(np.array([v.min(axis=0),v.max(axis=0)]))
        bounds=np.array([np.min([b[0] for b in boxes],axis=0),np.max([b[1] for b in boxes],axis=0)])
        shift=np.array([(bounds[0,0]+bounds[1,0])/2,(bounds[0,1]+bounds[1,1])/2,bounds[0,2]])
        bounds-=shift
        assert np.allclose(mesh.bounds,bounds,atol=.002,rtol=0),path
        volume=sum(expected[name]['volume_mm3'] for name in names)
        assert np.isclose(mesh.volume,volume,rtol=.001,atol=.01),(path,mesh.volume,volume)
        result.append({'file':str(path.relative_to(ROOT)), 'triangles':len(mesh.faces),
                       'connected_components':int(mesh.body_count),
                       'watertight':bool(mesh.is_watertight),'winding_consistent':bool(mesh.is_winding_consistent),
                       'dimensions_mm':list(mesh.extents),'volume_mm3':float(mesh.volume)})
    (ROOT/'spec/export_report.json').write_text(json.dumps({'stl_count':len(result),'units':'mm','files':result},ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'Round-trip validated {len(result)} STL files: manifold, finite, mm dimensions and volumes')

if __name__=='__main__': main()
