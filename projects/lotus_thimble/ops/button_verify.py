"""Measure the oval, normal wall thickness, concave neck, four pits and X."""
import os
import json
import math
import runpy
import bpy
import bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
import s3d


def run(ctx):
    p=ctx.params; obj=next(iter(ctx.targets.values()))["object"]
    g=runpy.run_path(os.path.join(ctx.proj_dir,"ops","geometry.py"))
    mesh=obj.data; world=[obj.matrix_world@v.co for v in mesh.vertices]
    tree=BVHTree.FromPolygons(world,[tuple(f.vertices) for f in mesh.polygons])
    def hit(origin,direction):
        result=tree.ray_cast(Vector(tuple(c*s3d.CM for c in origin)),Vector(direction))
        assert result[0] is not None,("Ray missed",origin,direction)
        return Vector(tuple(c/s3d.CM for c in result[0]))
    tol=p["tolerance"]; a=p["bore_x"]/2; b=p["bore_z"]/2; wall=p["wall"]; hw=p["band_w"]/2
    topo=s3d.manifold_report(obj.name)
    assert topo["boundary"]==topo["nonmanifold"]==0,topo
    bm=bmesh.new();bm.from_mesh(mesh);unseen=set(bm.verts);components=0
    while unseen:
        components+=1;stack=[unseen.pop()]
        while stack:
            v=stack.pop()
            for e in v.link_edges:
                other=e.other_vert(v)
                if other in unseen:unseen.remove(other);stack.append(other)
    volume=bm.calc_volume(signed=True)/s3d.CM**3;bm.free()
    assert components==1 and volume>0,(components,volume)
    bbox=s3d.bbox(obj.name)
    expected=[max(p["pad_d"],2*(a+wall)),max(p["pad_d"],p["band_w"]),p["rim_z"]+b+wall]
    assert all(abs(x-y)<tol for x,y in zip(bbox["size"],expected)),(bbox,expected)
    bx=hit((0,0,0),(1,0,0)).x-hit((0,0,0),(-1,0,0)).x
    bz=hit((0,0,0),(0,0,1)).z-hit((0,0,0),(0,0,-1)).z
    assert abs(bx-p["bore_x"])<tol and abs(bz-p["bore_z"])<tol,(bx,bz)
    oval=[];walls=[];rounds=[]
    for j in range(32):
        angle=2*math.pi*j/32; x=a*math.cos(angle); z=b*math.sin(angle)
        point=Vector((x,0,z));direction=point.normalized()
        actual=hit((0,0,0),direction)
        error=(actual-point).length; assert error<tol,("Oval",angle,error)
        oval.append({"angle":angle,"error_cm":error})
    # Unmodified lower half: the outer surface is the inner ellipse + wall*N.
    for j in range(17):
        angle=math.pi+math.pi*j/16; x=a*math.cos(angle);z=b*math.sin(angle)
        point=Vector((x,0,z));normal=Vector((math.cos(angle)/a,0,math.sin(angle)/b)).normalized()
        start=point+normal*(wall/2)
        actual=hit(start,normal)
        thickness=(actual-point).dot(normal)
        assert abs(thickness-wall)<tol,("Normal wall",angle,thickness)
        walls.append({"angle":angle,"thickness_cm":thickness})
        for side in (-1,1):
            for fraction in (.25,.5,.75,.95):
                er=p["outer_edge_r"]; y=side*(hw-er+er*fraction)
                offset=wall-er+er*math.sqrt(1-fraction*fraction)
                target=point+normal*offset;target.y=y
                start=point+normal*(wall+p["probe"]);start.y=y
                actual=hit(start,-normal);error=(actual-target).length
                assert error<tol,("End round",angle,y,error)
                rounds.append(error)
    z_band=-(b+wall/2)
    band=hit((0,hw+p["probe"],z_band),(0,-1,0)).y-hit((0,-hw-p["probe"],z_band),(0,1,0)).y
    assert abs(band-p["band_w"])<tol,band
    neck=[]
    for z in p["neck_probe_z"]:
        expected_x=g["profile_x"](p["support_curves"],z)
        for side in (-1,1):
            actual=side*hit((side*(p["pad_d"]+p["probe"]),0,z),(-side,0,0)).x
            assert abs(actual-expected_x)<tol,("Concave neck",z,actual,expected_x)
            neck.append({"z_cm":z,"side":side,"measured_x_cm":actual,"expected_x_cm":expected_x})
    neck_x=g["profile_x"](p["support_curves"],p["support_curves"][0][-1][1])
    assert neck_x<a+wall and neck_x<p["pad_d"]/2,"Inward neck missing"
    records=json.loads(obj["needle_pits"]);assert len(records)==4
    pits=[];floor_samples=[]
    for rec,position in zip(records,p["pit_positions"]):
        x,y=position;assert abs(rec["x_cm"]-x)<tol and abs(rec["y_cm"]-y)<tol
        floor=hit((x,y,p["rim_z"]+p["probe"]),(0,0,-1)).z
        depth=rec["surface_z_cm"]-floor
        assert abs(depth-p["pit_depth"])<tol,("Pit blocked or shallow",position,depth)
        for dx,dy in ((0,0),(p["pit_d"]/5,0),(-p["pit_d"]/5,0),(0,p["pit_d"]/5),(0,-p["pit_d"]/5)):
            px=x+dx;py=y+dy
            top=hit((px,py,p["rim_z"]+p["probe"]),(0,0,-1)).z
            roof=hit((px,py,0),(0,0,1)).z
            thickness=top-roof;assert thickness>=p["core"]-tol,("Pit floor thin",px,py,thickness)
            floor_samples.append(thickness)
        pits.append({**rec,"measured_floor_z_cm":floor,"measured_depth_cm":depth})
    # A free outer-side patch in each eye must still accept a needle tail.
    usable=[]
    for x,y in p["pit_positions"]:
        v=Vector((x,y)).normalized();px=x+v.x*p["pit_d"]/4;py=y+v.y*p["pit_d"]/4
        floor=hit((px,py,p["rim_z"]+p["probe"]),(0,0,-1)).z
        surface=p["bowl_center_z"]-math.sqrt(p["bowl_r"]**2-px*px-py*py)
        assert surface-floor>p["pit_depth"]/2,("Usable pit region obstructed",px,py)
        usable.append({"x_cm":px,"y_cm":py,"available_depth_cm":surface-floor})
    stitches=json.loads(obj["threads"]);assert len(stitches)==2
    threads=[]
    for index,rec in enumerate(stitches):
        for t in (.25,.5,.75):
            ends=rec["ends_cm"];x=ends[0][0]+t*(ends[1][0]-ends[0][0]);y=ends[0][1]+t*(ends[1][1]-ends[0][1])
            # The upper ridge owns the common crossing.
            if index==0 and t==.5:continue
            surface=p["bowl_center_z"]-math.sqrt(p["bowl_r"]**2-x*x-y*y)
            bump=p["cross_raise"]*math.exp(-((t-.5)/p["cross_span"])**2) if index==1 else 0
            actual=hit((x,y,p["rim_z"]+p["probe"]),(0,0,-1)).z
            height=actual-surface
            assert abs(height-p["thread_width"]/2-bump)<tol,("Thread height",index,t,height,bump)
            threads.append({"index":index,"t":t,"height_cm":height,"nominal_height_cm":p["thread_width"]/2+bump})
    # Independent side shoulder and upper round-lip probes.
    pr=p["pad_d"]/2;rise=p["rim_z"]-p["lip_h"]-b-wall;runout=pr-hw
    length=math.hypot(rise,runout);ux=runout/length;uz=rise/length
    tangent=p["shoulder_r"]*(1-uz)/ux;z0=b+wall-tangent;z1=b+wall+tangent*uz
    shoulders=[]
    for f in (.25,.5,.75):
        z=z0+(z1-z0)*f;expected_y=hw+p["shoulder_r"]-math.sqrt(p["shoulder_r"]**2-(z-z0)**2)
        # The low shoulder is below the oval's central roof; sample on the
        # flat end-face land outside the bore, rather than through the hole.
        actual=hit((p["shoulder_probe_x"],pr+p["probe"],z),(0,-1,0)).y
        assert abs(actual-expected_y)<tol,("Shoulder",z,actual,expected_y)
        shoulders.append({"x_cm":p["shoulder_probe_x"],"z_cm":z,"measured_y_cm":actual,"expected_y_cm":expected_y})
    lr=p["lip_r"];z=p["rim_z"]-lr/2;expected_y=pr-lr+math.sqrt(lr**2-(lr/2)**2)
    actual=hit((0,pr+p["probe"],z),(0,-1,0)).y
    assert abs(actual-expected_y)<tol,("Lip",actual,expected_y)
    land=float(obj["top_land_cm"]);assert land>=p["min_land"]-tol,land
    bowl_center=p["bowl_center_z"]-p["bowl_r"]
    report={"object":obj.name,"blender_version":bpy.app.version_string,"units":"cm","bbox":bbox,"expected_size_cm":expected,"topology":topo,"connected_components":components,"volume_cm3":volume,"bore_x_cm":bx,"bore_z_cm":bz,"oval_probes":oval,"wall_normal_probes":walls,"band_width_cm":band,"end_round_max_error_cm":max(rounds),"end_round_probe_count":len(rounds),"neck_probes":neck,"pits":pits,"min_sampled_pit_floor_thickness_cm":min(floor_samples),"pit_floor_sample_count":len(floor_samples),"usable_pit_probes":usable,"threads":stitches,"thread_probes":threads,"shoulder_probes":shoulders,"top_flat_land_cm":land,"bowl_depth_cm":p["rim_z"]-bowl_center,"central_body_thickness_cm":bowl_center-b,"tolerance_cm":tol,"physical_fit_and_strength":"not tested"}
    with open(os.path.join(ctx.proj_dir,"spec","verification_report.json"),"w",encoding="utf-8") as f:json.dump(report,f,ensure_ascii=False,indent=2)
    print("VERIFIED_BUTTON",json.dumps({k:report[k] for k in ("topology","bore_x_cm","bore_z_cm","band_width_cm","min_sampled_pit_floor_thickness_cm","volume_cm3")}),flush=True)
