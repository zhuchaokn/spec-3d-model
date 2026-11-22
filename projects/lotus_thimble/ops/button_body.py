"""Constant-normal-thickness oval band and confirmed concave lotus support."""
import os
import runpy
import math
import bpy
import s3d


def run(ctx):
    g=runpy.run_path(os.path.join(ctx.proj_dir,"ops","geometry.py"))
    mesh=g["mesh_object"]; arc=g["arc"]; revolve=g["revolve"]; boolean=g["boolean_closed"]
    ex=g["ellipse_x"]; solid=g["ellipse_solid"]; px=g["profile_x"]
    p=ctx.params
    a=p["bore_x"]/2; b=p["bore_z"]/2; w=p["wall"]
    hw=p["band_w"]/2; pr=p["pad_d"]/2; rr=b+w
    er=p["outer_edge_r"]; ir=p["bore_edge_r"]
    n=int(p["segments"]); m=int(p["arc_segments"]); merge=p["merge_distance"]
    profile=[(w-er,-hw)]
    profile+=arc((w-er,-hw+er),er,-math.pi/2,0,m)[1:]
    profile.append((w,hw-er))
    profile+=arc((w-er,hw-er),er,0,math.pi/2,m)[1:]
    obj=solid(ctx.name,a,b,profile,n,ctx.center,merge)
    # Retain the exact lower band; replace the upper exterior by one continuous
    # section loft so the former boolean intersection cannot remain a ridge.
    ext=pr+p["extension"]
    boolean(obj,s3d.add_box("_UpperBandCut",(2*ext,2*ext,2*ext),
                          (ctx.center[0],ctx.center[1],ctx.center[2]+ext)),operation="DIFFERENCE")

    top=p["rim_z"]; lipbase=top-p["lip_h"]
    rise=lipbase-rr; runout=pr-hw
    length=math.hypot(runout,rise); ux=runout/length; uz=rise/length
    small=p["lower_r"]; shoulder=p["shoulder_r"]
    small_t=small*math.tan(math.acos(uz)/2); big_t=shoulder*(1-uz)/ux
    assert rise>0 and runout>0 and length>small_t+big_t
    zs=rr-big_t; yc=hw+shoulder
    big_end=(hw+big_t*ux,rr+big_t*uz)
    small_start=(pr-small_t*ux,lipbase-small_t*uz)
    small_center=(pr-small,lipbase+small_t)
    def x_half(z):
        return px(p["support_curves"],z)
    def y_half(z):
        if z<=zs: return hw
        if z<=big_end[1]: return yc-math.sqrt(max(0,shoulder**2-(z-zs)**2))
        if z<=small_start[1]: return big_end[0]+(z-big_end[1])*ux/uz
        if z<=small_center[1]: return small_center[0]+math.sqrt(max(0,small**2-(z-small_center[1])**2))
        return pr
    loft_top=top-p["lip_r"]
    levels={-p["step"],0,zs,big_end[1],small_start[1],small_center[1],lipbase,loft_top,p["blend_start"],p["blend_end"],rr,
            p["junction_blend_start"],p["junction_blend_full"]}
    levels.update(c[-1][1] for c in p["support_curves"])
    steps=math.ceil(loft_top/p["step"])
    levels.update(loft_top*j/steps for j in range(steps+1))
    levels=sorted(z for z in levels if -p["step"]<=z<=loft_top)
    verts=[]; faces=[]; nl=int(p["loft_segments"]);quarter=nl//4;radii=[]
    for z in levels:
        xh=x_half(z); yh=y_half(z)
        # Round the four shoulders before they reach the pad underside.
        # The quintic blend has zero first/second derivative at either end;
        # the independent oval band union preserves the normal wall thickness.
        t=max(0,min(1,(z-p["blend_start"])/(p["blend_end"]-p["blend_start"])))
        smooth=t**3*(10-15*t+6*t*t)
        cr=er+(min(xh,yh)-er)*smooth
        outline=[]
        for q in range(4):
            sx=1 if q in (0,3) else -1; sy=1 if q in (0,1) else -1
            for j in range(quarter):
                angle=(q+j/(quarter-1))*math.pi/2
                offset=w-er+er*abs(math.cos(angle))
                # Carry the exact oval band's normal-offset end round into
                # the support; above the band use the small XY corner round.
                delta=ex(a,b,z,w)-ex(a,b,z,offset) if z<b+w-er else er*(1-abs(math.cos(angle)))
                lower_x=sx*(xh-delta); lower_y=sy*(yh-er+er*abs(math.sin(angle)))
                upper_x=sx*(xh-cr)+cr*math.cos(angle)
                upper_y=sy*(yh-cr)+cr*math.sin(angle)
                outline.append(((1-smooth)*lower_x+smooth*upper_x,(1-smooth)*lower_y+smooth*upper_y))
        support=g["radial_polygon"](outline)
        band=g["oval_section"](a,b,z,w,er,hw,m)
        jt=max(0,min(1,(z-p["junction_blend_start"])/(p["junction_blend_full"]-p["junction_blend_start"])))
        blend=jt**3*(10-15*jt+6*jt*jt)
        row=[]
        for j in range(nl):
            angle=2*math.pi*j/nl
            radius=support(angle)
            if z<=0:radius=band(angle)
            elif band is not None:
                # Keep the approved front silhouette; smooth the actual end
                # shoulders in all four quadrants, with no separate union seam.
                radius=g["smooth_max"](radius,band(angle),p["junction_blend_r"]*blend*math.sin(2*angle)**2)
            row.append(radius)
        radii.append(row)
    # Smooth the four longitudinal shoulder profiles as geometry. Normal
    # averaging alone would conceal the ridge but leave it in the printed STL.
    # Integrate a Gaussian over the irregular Z samples; preserve both approved
    # axial silhouettes and fade smoothly into the untouched lower band/lip.
    sigma=p["junction_smooth_sigma"]
    dz=[(levels[min(i+1,len(levels)-1)]-levels[max(0,i-1)])/2 for i in range(len(levels))]
    for i,z in enumerate(levels):
        jt=max(0,min(1,(z-p["junction_blend_start"])/(p["junction_blend_full"]-p["junction_blend_start"])))
        ft=max(0,min(1,(z-p["junction_smooth_fade_start"])/(p["junction_smooth_end"]-p["junction_smooth_fade_start"])))
        strength=jt**3*(10-15*jt+6*jt*jt)*(1-ft**3*(10-15*ft+6*ft*ft))
        weights=[(k,dz[k]*math.exp(-.5*((zk-z)/sigma)**2)) for k,zk in enumerate(levels) if abs(zk-z)<=4*sigma]
        total=sum(v for _,v in weights)
        for j in range(nl):
            angle=2*math.pi*j/nl;mix=strength*math.sin(2*angle)**2
            filtered=sum(radii[k][j]*weight for k,weight in weights)/total
            radius=radii[i][j]*(1-mix)+filtered*mix
            verts.append((radius*math.cos(angle),radius*math.sin(angle),z))
    faces.append(tuple(reversed(range(nl))))
    for i in range(len(levels)-1):
        for j in range(nl):
            k=(j+1)%nl; faces.append((i*nl+j,i*nl+k,(i+1)*nl+k,(i+1)*nl+j))
    faces.append(tuple((len(levels)-1)*nl+j for j in range(nl)))
    boolean(obj,mesh("_ConcaveSupport",verts,faces,ctx.center,merge))
    print("JOIN_SUPPORT",s3d.manifold_report(obj.name),flush=True)

    # Retain the original lotus bowl, broad land, and round lip at its scale.
    profile=[(0,p["base_z"]),big_end,small_start]
    sa=math.atan2(small_start[1]-small_center[1],small_start[0]-small_center[0])
    profile+=arc(small_center,small,sa,0,m)[1:]
    profile.append((pr,top-p["lip_r"]))
    profile+=arc((pr-p["lip_r"],top-p["lip_r"]),p["lip_r"],0,math.pi/2,m)[1:]
    br=p["bowl_r"]; bz=p["bowl_center_z"]; be=p["bowl_edge_r"]
    fz=top-be; fr=math.sqrt((br+be)**2-(bz-fz)**2)
    end=(fr*br/(br+be),bz+(fz-bz)*br/(br+be))
    profile.append((fr,top)); ea=math.atan2(end[1]-fz,end[0]-fr)
    profile+=arc((fr,fz),be,math.pi/2,ea,m)[1:]
    for j in range(1,n//2+1):
        r=end[0]*(1-j/(n//2)); profile.append((r,bz-math.sqrt(br*br-r*r)))
    boolean(obj,revolve("_LotusButton",profile,"Z",n,ctx.center,merge))
    print("JOIN_BUTTON",s3d.manifold_report(obj.name),flush=True)
    cavity=[(0,bz-br)]
    for j in range(1,n//2+1):
        r=end[0]*j/(n//2); cavity.append((r,bz-math.sqrt(br*br-r*r)))
    cavity+=arc((fr,fz),be,ea,math.pi/2,m)[1:]
    cavity.extend([(fr,top+p["extension"]),(0,top+p["extension"])])
    boolean(obj,revolve("_BowlCut",cavity,"Z",n,ctx.center,merge),operation="DIFFERENCE")
    print("CUT_BOWL",s3d.manifold_report(obj.name),flush=True)

    ext=pr+p["extension"]
    profile=[(ir,-ext),(ir,-hw)]
    profile+=arc((ir,-hw+ir),ir,-math.pi/2,-math.pi,m)[1:]
    profile.append((0,hw-ir))
    profile+=arc((ir,hw-ir),ir,math.pi,math.pi/2,m)[1:]
    profile.append((ir,ext))
    boolean(obj,solid("_OvalBore",a,b,profile,n,ctx.center,merge),operation="DIFFERENCE")
    topo=s3d.manifold_report(obj.name)
    assert topo["boundary"]==topo["nonmanifold"]==0,topo
    for f in obj.data.polygons: f.use_smooth=True
    obj["top_land_cm"]=pr-p["lip_r"]-fr
    print("BUTTON_BODY",s3d.inspect(obj.name),topo,flush=True)
