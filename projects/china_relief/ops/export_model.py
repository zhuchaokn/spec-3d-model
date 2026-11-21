"""Export bed-sized print pieces and clearly separate province assemblies."""
import os
import numpy as np
import bpy


def run(ctx):
    out=os.path.join(ctx.proj_dir,'output')
    os.makedirs(out,exist_ok=True)
    for filename,names in ctx.params['pieces'].items():
        path=os.path.join(out,filename+'.stl')
        os.makedirs(os.path.dirname(path),exist_ok=True)
        triangles=[]
        for name in names:
            obj=bpy.data.objects.get(name)
            if obj is None:
                raise RuntimeError(f'Missing export object: {name}')
            # Preserve sub-nozzle source components: Blender and binary STL use float32.
            # These objects are unchanged prepared meshes, stored as float64; their
            # named scene objects provide the source and assembly transform.
            with np.load(obj['prepared_mesh'],allow_pickle=False) as data:
                verts=data['vertices']*10  # cm -> mm
                idx=data['faces']
            matrix=np.asarray(obj.matrix_world,dtype='float64')
            verts=sum(verts[:,j,None]*matrix[None,:3,j] for j in range(3))+matrix[:3,3]*1000
            triangles.append(verts[idx])
        tris=np.concatenate(triangles)
        # Print on a flat bed and keep coordinates near zero; assembly lives in blend.
        lo=tris.min(axis=(0,1)); hi=tris.max(axis=(0,1))
        tris-=np.array([(lo[0]+hi[0])/2,(lo[1]+hi[1])/2,lo[2]])
        normal=np.cross(tris[:,1]-tris[:,0],tris[:,2]-tris[:,0])
        normal/=np.linalg.norm(normal,axis=1)[:,None]
        assert np.isfinite(normal).all(),path
        # ASCII precision avoids destroying tiny source rings during float32 export.
        with open(path,'w',encoding='ascii') as f:
            f.write('solid china_relief_units_mm\n')
            for n,tri in zip(normal,tris):
                f.write('facet normal '+ ' '.join(format(v,'.12g') for v in n)+'\nouter loop\n')
                for vertex in tri:
                    f.write('vertex '+' '.join(format(v,'.12g') for v in vertex)+'\n')
                f.write('endloop\nendfacet\n')
            f.write('endsolid china_relief_units_mm\n')
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out,ctx.params['blend_name']))
    print(f'Exported {len(ctx.params["pieces"])} STL files (millimetres) and blend',flush=True)
