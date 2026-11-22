"""Two closed, bowl-following thread ridges; upper crossing stays embedded."""
import os
import math
import json
import runpy
import bpy
from mathutils import Vector
import s3d


def run(ctx):
    g=runpy.run_path(os.path.join(ctx.proj_dir,"ops","geometry.py"))
    p=ctx.params; obj=next(iter(ctx.targets.values()))["object"]
    radius=p["width"]/2; records=[]
    for index,ends in enumerate(p["paths"]):
        def point(t):
            x=ends[0][0]+(ends[1][0]-ends[0][0])*t
            y=ends[0][1]+(ends[1][1]-ends[0][1])*t
            z=p["bowl_center_z"]-math.sqrt(p["bowl_r"]**2-x*x-y*y)
            bump=p["cross_raise"]*math.exp(-((t-.5)/p["cross_span"])**2) if index==1 else 0
            return Vector((x,y,z+bump))
        length=math.dist(ends[0],ends[1]); steps=math.ceil(length/p["step"])
        n=int(p["segments"]); verts=[]; faces=[]
        horizontal=Vector((ends[1][0]-ends[0][0],ends[1][1]-ends[0][1],0)).normalized()
        normal=Vector((-horizontal.y,horizontal.x,0))
        for i in range(steps+1):
            t=i/steps; c=point(t)
            tangent=(point(min(1,t+1/steps))-point(max(0,t-1/steps))).normalized()
            vertical=tangent.cross(normal).normalized()
            for j in range(n):
                angle=2*math.pi*j/n
                verts.append(tuple(c+radius*(normal*math.cos(angle)+vertical*math.sin(angle))))
        faces.append(tuple(reversed(range(n))))
        for i in range(steps):
            for j in range(n):
                k=(j+1)%n;faces.append((i*n+j,i*n+k,(i+1)*n+k,(i+1)*n+j))
        faces.append(tuple(steps*n+j for j in range(n)))
        tube=g["mesh_object"](f"_Thread{index}",verts,faces,ctx.center,p["merge_distance"])
        for t in (0,1):
            center=point(t)+Vector(ctx.center)
            bpy.ops.mesh.primitive_uv_sphere_add(segments=n,ring_count=int(p["cap_rings"]),radius=radius*s3d.CM,location=tuple(v*s3d.CM for v in center))
            g["boolean_closed"](tube,bpy.context.object)
        g["boolean_closed"](obj,tube)
        topo=s3d.manifold_report(obj.name)
        assert topo["boundary"]==topo["nonmanifold"]==0,topo
        records.append({"ends_cm":ends,"width_cm":p["width"],"height_cm":radius,"cross_raise_cm":p["cross_raise"] if index==1 else 0})
        print("JOIN_THREAD",index,topo,flush=True)
    obj["threads"]=json.dumps(records)
    for f in obj.data.polygons:f.use_smooth=True
