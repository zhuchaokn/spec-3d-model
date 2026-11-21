"""Thimble body: rounded ring, filled loft shoulders, and revolved round lip.

All product dimensions come from ctx.params in centimeters. Profiles encode the
confirmed front/side sections; a rounded rectangle loft fills their 3D join.
No whole-object convex hull or global bevel is used.
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


def run(ctx):
    p=ctx.params
    n=int(p["segments"]); m=int(p["arc_segments"])
    rr=p["ring_r"]; hw=p["band_w"]/2; pr=p["pad_d"]/2
    er=p["outer_edge_r"]; ir=p["bore_edge_r"]
    merge=p["merge_distance"]
    # Solid ring outside with exact R0.6 round ends; the bore is cut after joins.
    profile=[(0,-hw),(rr-er,-hw)]
    profile+=arc((rr-er,-hw+er),er,-math.pi/2,0,m)[1:]
    profile.append((rr,hw-er))
    profile+=arc((rr-er,hw-er),er,0,math.pi/2,m)[1:]
    profile.append((0,hw))
    obj=revolve(ctx.name,profile,"Y",n,ctx.center,merge)

    top=p["rim_z"]; lipbase=top-p["lip_h"]
    rise=lipbase-rr; runout=pr-hw
    assert rise>0 and runout>0
    length=math.hypot(runout,rise); ux=runout/length; uz=rise/length
    small=p["lower_r"]; shoulder=p["shoulder_r"]
    small_t=small*math.tan(math.acos(uz)/2)
    big_t=shoulder*(1-uz)/ux
    assert length>small_t+big_t, "Shoulder and lip fillets overlap"
    zs=rr-big_t; yc=hw+shoulder
    big_end=(hw+big_t*ux,rr+big_t*uz)
    small_start=(pr-small_t*ux,lipbase-small_t*uz)
    small_center=(pr-small,lipbase+small_t)

    # Front support tangent from the lower lip to the outer ring circle.
    dsq=pr*pr+lipbase*lipbase
    a=rr*rr/dsq; b=rr*math.sqrt(dsq-rr*rr)/dsq
    tx=a*pr+b*lipbase; tz=a*lipbase-b*pr
    def x_half(z):
        if z<=tz:
            return math.sqrt(max(0,rr*rr-z*z))
        if z<=lipbase:
            return tx+(pr-tx)*(z-tz)/(lipbase-tz)
        return pr
    def y_half(z):
        if z<=zs:
            return hw
        if z<=big_end[1]:
            return yc-math.sqrt(max(0,shoulder*shoulder-(z-zs)**2))
        if z<=small_start[1]:
            return big_end[0]+(z-big_end[1])*ux/uz
        if z<=small_center[1]:
            return small_center[0]+math.sqrt(max(0,small*small-(z-small_center[1])**2))
        return pr
    loft_top=top-p["lip_r"]
    levels={0, tz, zs, big_end[1], small_start[1], lipbase, small_center[1], loft_top}
    steps=math.ceil(loft_top/p["step"])
    levels.update(loft_top*j/steps for j in range(steps+1))
    levels=sorted(z for z in levels if 0<=z<=loft_top)
    verts=[]; faces=[]; quarter=n//4
    for z in levels:
        xh=x_half(z); yh=y_half(z)
        t=max(0,min(1,(z-p["blend_start"])/(small_center[1]-p["blend_start"])))
        smooth=t*t*t*(10+t*(-15+6*t))
        cr=p["corner_min"]+(min(xh,yh)-p["corner_min"])*smooth
        radial_outer=math.hypot(xh,z)
        for q in range(4):
            sx=1 if q in (0,3) else -1
            sy=1 if q in (0,1) else -1
            for j in range(quarter):
                angle=(q+j/(quarter-1))*math.pi/2
                # Continue the ring's radial/Y end fillet through the filled
                # shoulder. An XY rounded rectangle protrudes beyond this
                # surface at z>0, restoring a sharp ledge after the union.
                radial_r=radial_outer-er+er*abs(math.cos(angle))
                lower_x=sx*math.sqrt(max(0,radial_r*radial_r-z*z))
                lower_y=sy*(yh-er+er*abs(math.sin(angle)))
                upper_x=sx*(xh-cr)+cr*math.cos(angle)
                upper_y=sy*(yh-cr)+cr*math.sin(angle)
                verts.append(((1-smooth)*lower_x+smooth*upper_x,
                              (1-smooth)*lower_y+smooth*upper_y,z))
    faces.append(tuple(reversed(range(n))))
    for i in range(len(levels)-1):
        for j in range(n):
            k=(j+1)%n
            faces.append((i*n+j,i*n+k,(i+1)*n+k,(i+1)*n+j))
    faces.append(tuple((len(levels)-1)*n+j for j in range(n)))
    support=mesh_object("_FilledShoulders",verts,faces,ctx.center,merge)
    boolean_closed(obj,support)
    print("JOIN_SHOULDER",s3d.manifold_report(obj.name),flush=True)

    # Round lip is revolved: R0.4 below, a real short wall, then R0.8 above.
    profile=[(0,p["base_z"]),big_end,small_start]
    sa=math.atan2(small_start[1]-small_center[1],small_start[0]-small_center[0])
    profile+=arc(small_center,small,sa,0,m)[1:]
    profile.append((pr,top-p["lip_r"]))
    profile+=arc((pr-p["lip_r"],top-p["lip_r"]),p["lip_r"],0,math.pi/2,m)[1:]
    # R0.3 blends the horizontal land into the spherical bowl exactly.
    br=p["bowl_r"]; bz=p["bowl_center_z"]; be=p["bowl_edge_r"]
    fz=top-be
    fr=math.sqrt((br+be)**2-(bz-fz)**2)
    end=(fr*br/(br+be),bz+(fz-bz)*br/(br+be))
    profile.append((fr,top))
    ea=math.atan2(end[1]-fz,end[0]-fr)
    profile+=arc((fr,fz),be,math.pi/2,ea,m)[1:]
    for j in range(1,n//2+1):
        r=end[0]*(1-j/(n//2))
        profile.append((r,bz-math.sqrt(br*br-r*r)))
    pad=revolve("_RoundedNeedlePad",profile,"Z",n,ctx.center,merge)
    boolean_closed(obj,pad)
    print("JOIN_PAD",s3d.manifold_report(obj.name),flush=True)
    # Restore the bowl after union: the solid shoulder loft overlaps its floor.
    cavity=[(0,bz-br)]
    for j in range(1,n//2+1):
        r=end[0]*j/(n//2)
        cavity.append((r,bz-math.sqrt(br*br-r*r)))
    cavity+=arc((fr,fz),be,ea,math.pi/2,m)[1:]
    cavity.extend([(fr,top+p["extension"]),(0,top+p["extension"])])
    s3d.bool_diff(obj,revolve("_BowlCavity",cavity,"Z",n,ctx.center,merge))
    print("CUT_BOWL",s3d.manifold_report(obj.name),flush=True)
    # R0.6 flared bore entrances, tool caps far beyond the physical part.
    radius=p["bore_d"]/2
    ext=pr+p["extension"]
    profile=[(0,-ext),(radius+ir,-ext),(radius+ir,-hw)]
    profile+=arc((radius+ir,-hw+ir),ir,-math.pi/2,-math.pi,m)[1:]
    profile.append((radius,hw-ir))
    profile+=arc((radius+ir,hw-ir),ir,math.pi,math.pi/2,m)[1:]
    profile.extend([(radius+ir,ext),(0,ext)])
    tool=revolve("_RoundedBore",profile,"Y",n,ctx.center,merge)
    boolean_closed(obj,tool,operation="DIFFERENCE")
    print("CUT_BORE",s3d.manifold_report(obj.name),flush=True)
    # Closed CSG is already manifold. Welding nearby boolean vertices can
    # collapse valid narrow faces at some bore diameters and open the mesh.
    topology=s3d.manifold_report(obj.name)
    assert topology["boundary"]==topology["nonmanifold"]==0,topology
    for face in obj.data.polygons:
        face.use_smooth=True
    obj["top_land_cm"]=pr-p["lip_r"]-fr
    obj["lip_height_cm"]=p["lip_h"]
    obj["lip_radius_cm"]=p["lip_r"]
    obj["shoulder_radius_cm"]=shoulder
    print("BODY",s3d.inspect(obj.name),s3d.manifold_report(obj.name))
