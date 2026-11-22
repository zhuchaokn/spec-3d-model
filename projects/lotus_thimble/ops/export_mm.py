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
    records=[]; pending={}; cancelled=0
    for face in bm.faces:
        v=[obj.matrix_world@a.co for a in face.verts]
        coords=[c*1000 for a in v for c in a]
        # Inspect the actual float32 coordinates STL will retain. CSG can
        # leave opposite thin-fold triangles that become exactly coincident
        # at this precision; cancel only exact opposite pairs, never holes.
        coords=struct.unpack("<9f",struct.pack("<9f",*coords))
        vertices=[tuple(coords[j:j+3]) for j in (0,3,6)]
        key=tuple(sorted(vertices))
        order=[key.index(a) for a in vertices]
        sign=(-1)**sum(order[i]>order[j] for i in range(3) for j in range(i+1,3))
        opposite=pending.get((key,-sign))
        if opposite:
            records[opposite.pop()]=None;cancelled+=2
            continue
        normal=(v[1]-v[0]).cross(v[2]-v[0]).normalized()
        pending.setdefault((key,sign),[]).append(len(records))
        records.append(struct.pack("<12fH",*normal,*coords,0))
    records=[record for record in records if record is not None]
    # STL carries no units: convert Blender meters explicitly to mm.
    with open(path,"wb") as f:
        f.write(b"spec-3d-model lotus thimble; coordinates in millimeters".ljust(80,b" "))
        f.write(struct.pack("<I",len(records)))
        for record in records:f.write(record)
    bm.free()
    obj["stl_cancelled_opposite_triangles"]=cancelled
    s3d.sel(obj)
    s3d.save_blend(os.path.join(folder,p["blend_name"]))
    print("EXPORTED_MM",path,"cancelled_opposite_triangles",cancelled)
