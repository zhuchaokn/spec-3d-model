"""Project helpers for closed meshes, oval offsets, profiles and manifold CSG.

Product dimensions are passed by project ops from the JSON registry in cm.
Loaded with runpy on each operation so saved edits take effect immediately.
"""
import math
import bpy
import bmesh
import s3d


def mesh_object(name, vertices, faces, center, merge):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple((a+b)*s3d.CM for a,b in zip(v,center)) for v in vertices], [], faces)
    me.update()
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=merge*s3d.CM)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(obj)
    print("MESH",name,s3d.manifold_report(name),flush=True)
    return obj


def revolve(name, profile, axis, n, center, merge):
    verts, loops, faces = [], [], []
    for r,z in profile:
        if abs(r) < merge:
            loops.append([len(verts)])
            verts.append((0,z,0) if axis == "Y" else (0,0,z))
        else:
            ids=[]
            for j in range(n):
                a=2*math.pi*j/n
                ids.append(len(verts))
                verts.append((r*math.cos(a),z,r*math.sin(a)) if axis == "Y" else (r*math.cos(a),r*math.sin(a),z))
            loops.append(ids)
    for a,b in zip(loops,loops[1:]+loops[:1]):
        if len(a)==len(b)==1:
            continue
        for j in range(n):
            k=(j+1)%n
            if len(a)==1:
                faces.append((a[0],b[j],b[k]))
            elif len(b)==1:
                faces.append((a[j],b[0],a[k]))
            else:
                faces.append((a[j],b[j],b[k],a[k]))
    return mesh_object(name,verts,faces,center,merge)


def arc(center, radius, a0, a1, n):
    return [(center[0]+radius*math.cos(a0+(a1-a0)*j/n),
             center[1]+radius*math.sin(a0+(a1-a0)*j/n)) for j in range(n+1)]


def boolean_closed(target, other, operation="UNION"):
    """Manifold CSG handles coincident tangent surfaces of closed inputs."""
    s3d.sel(target)
    mod=target.modifiers.new("ClosedBoolean", "BOOLEAN")
    mod.operation=operation
    mod.solver="MANIFOLD"
    mod.object=other
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(other,do_unlink=True)


def ellipse_point(a, b, angle, offset=0):
    c=math.cos(angle); s=math.sin(angle)
    nx=c/a; nz=s/b; length=math.hypot(nx,nz)
    return (a*c+offset*nx/length,b*s+offset*nz/length)


def ellipse_x(a,b,z,offset):
    if abs(z)>=b+offset:
        return 0
    lo=0; hi=math.pi/2
    for _ in range(48):
        angle=(lo+hi)/2
        if ellipse_point(a,b,angle,offset)[1]<abs(z): lo=angle
        else: hi=angle
    return ellipse_point(a,b,(lo+hi)/2,offset)[0]


def ellipse_solid(name,a,b,profile,n,center,merge):
    verts=[]; faces=[]
    for offset,y in profile:
        for j in range(n):
            x,z=ellipse_point(a,b,2*math.pi*j/n,offset)
            verts.append((x,y,z))
    faces.append(tuple(reversed(range(n))))
    for i in range(len(profile)-1):
        for j in range(n):
            k=(j+1)%n
            faces.append((i*n+j,i*n+k,(i+1)*n+k,(i+1)*n+j))
    faces.append(tuple((len(profile)-1)*n+j for j in range(n)))
    return mesh_object(name,verts,faces,center,merge)


def bezier_point(points,t):
    s=1-t
    return tuple(s**3*points[0][i]+3*s*s*t*points[1][i]+3*s*t*t*points[2][i]+t**3*points[3][i] for i in (0,1))


def profile_x(curves,z):
    for curve in curves:
        if z<=curve[-1][1]:
            lo=0; hi=1
            for _ in range(48):
                t=(lo+hi)/2
                if bezier_point(curve,t)[1]<z: lo=t
                else: hi=t
            return bezier_point(curve,(lo+hi)/2)[0]
    return curves[-1][-1][0]
