"""Binary STL in explicit millimeters; keep Blender's centimeter design scene."""
import os
import struct
import bpy
import bmesh
import s3d


def run(ctx):
    p=ctx.params
    obj=next(iter(ctx.targets.values()))["object"]
    folder=os.path.join(ctx.proj_dir,p["out_dir"])
    os.makedirs(folder,exist_ok=True)
    bm=bmesh.new();bm.from_mesh(obj.data)
    bmesh.ops.triangulate(bm,faces=list(bm.faces))
    path=os.path.join(folder,p["stl_name"])
    # STL carries no units: convert Blender meters explicitly to mm.
    with open(path,"wb") as f:
        f.write(b"spec-3d-model lotus thimble; coordinates in millimeters".ljust(80,b" "))
        f.write(struct.pack("<I",len(bm.faces)))
        for face in bm.faces:
            v=[obj.matrix_world@a.co for a in face.verts]
            normal=(v[1]-v[0]).cross(v[2]-v[0]).normalized()
            coords=[c*1000 for a in v for c in a]
            f.write(struct.pack("<12fH",*normal,*coords,0))
    bm.free()
    s3d.sel(obj)
    s3d.save_blend(os.path.join(folder,p["blend_name"]))
    print("EXPORTED_MM",path)
