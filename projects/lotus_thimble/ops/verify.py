"""Measured topology, BVH rays, dimensions, wall thickness and dimple depths."""
import json
import os
import math
import bpy
import bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
import s3d


def measure_junction(tree, p):
    """Check both ends/sides against the radial end-round, including z=0.

    This independent analytic profile catches the former XY-loft ledge even
    when the final union is watertight and has the correct bounding box.
    """
    rr=p["ring_r"]; pr=p["pad_d"]/2; hw=p["band_w"]/2
    er=p["outer_edge_r"]; lipbase=p["rim_z"]-p["lip_h"]
    dsq=pr*pr+lipbase*lipbase
    a=rr*rr/dsq; b=rr*math.sqrt(dsq-rr*rr)/dsq
    tx=a*pr+b*lipbase; tz=a*lipbase-b*pr
    probes=[]
    heights=[-p["tolerance"],0,p["tolerance"]]
    heights.extend(p["blend_start"]*f for f in (0.25,0.5,0.75,0.9))
    for z in heights:
        xh=math.sqrt(rr*rr-z*z) if z<=tz else tx+(pr-tx)*(z-tz)/(lipbase-tz)
        rs=math.hypot(xh,z)
        for fraction in (0.25,0.5,0.75,0.95):
            y=hw-er+er*fraction
            radius=rs-er+er*math.sqrt(1-fraction*fraction)
            expected=math.sqrt(radius*radius-z*z)
            for sx in (-1,1):
                for sy in (-1,1):
                    origin=Vector((sx*(rr+p["probe"])*s3d.CM,sy*y*s3d.CM,z*s3d.CM))
                    result=tree.ray_cast(origin,Vector((-sx,0,0)))
                    assert result[0] is not None, ("Junction ray missed",z,y)
                    actual=sx*result[0].x/s3d.CM
                    error=abs(actual-expected)
                    assert error<p["tolerance"], ("End fillet ledge",z,sy*y,sx,actual,expected,error)
                    probes.append({"z_cm":z,"y_cm":sy*y,"side":sx,
                                   "measured_x_abs_cm":actual,"expected_x_abs_cm":expected,
                                   "error_cm":error})
    return {"radius_cm":er,"max_error_cm":max(r["error_cm"] for r in probes),"probes":probes}


def run(ctx):
    p=ctx.params
    obj=next(iter(ctx.targets.values()))["object"]
    bpy.context.view_layer.update()
    mesh=obj.data
    verts=[obj.matrix_world@v.co for v in mesh.vertices]
    tree=BVHTree.FromPolygons(verts,[tuple(f.vertices) for f in mesh.polygons],all_triangles=False)
    def hit(origin,direction):
        result=tree.ray_cast(Vector(tuple(c*s3d.CM for c in origin)),Vector(direction))
        assert result[0] is not None, f"Ray missed {origin} {direction}"
        return tuple(c/s3d.CM for c in result[0])
    bm=bmesh.new();bm.from_mesh(mesh)
    unseen=set(bm.verts); components=[]
    while unseen:
        stack=[unseen.pop()];count=0
        while stack:
            v=stack.pop();count+=1
            for e in v.link_edges:
                u=e.other_vert(v)
                if u in unseen:
                    unseen.remove(u);stack.append(u)
        components.append(count)
    volume=bm.calc_volume(signed=True)/s3d.CM**3
    bm.free()
    topo=s3d.manifold_report(obj.name)
    assert topo["boundary"]==topo["nonmanifold"]==0,topo
    assert len(components)==1,components
    assert volume>0,volume
    box=s3d.bbox(obj.name)
    expected=[2*p["ring_r"],max(p["pad_d"],p["band_w"]),p["rim_z"]+p["ring_r"]]
    tol=p["tolerance"]
    for measured,wanted in zip(box["size"],expected):
        assert abs(measured-wanted)<tol,(box,expected)
    hole_up=hit((0,0,0),(0,0,1))[2]
    hole_down=hit((0,0,0),(0,0,-1))[2]
    bore=hole_up-hole_down
    assert abs(bore-p["bore_d"])<tol,(bore,p["bore_d"])
    records=json.loads(obj["needle_pits"])
    assert len(records)==int(p["count"])+1
    measured_pits=[]
    for rec in records:
        x=rec["x_cm"];y=rec["y_cm"]
        floor=hit((x,y,p["rim_z"]+p["probe"]),(0,0,-1))[2]
        depth=rec["surface_z_cm"]-floor
        assert abs(depth-p["pit_depth"])<tol,(rec,floor,depth)
        measured_pits.append({**rec,"measured_floor_z_cm":floor,"measured_depth_cm":depth})
    core=measured_pits[0]["measured_floor_z_cm"]-hole_up
    assert abs(core-p["core"])<tol,(core,p["core"])
    junction=measure_junction(tree,p)
    # Probe fillet geometry from actual mesh vertices, not only stored metadata.
    rim_points=[]
    pr=p["pad_d"]/2; lr=p["lip_r"]
    for v in verts:
        x,y,z=(a/s3d.CM for a in v)
        r=math.hypot(x,y)
        if r>=pr-lr-tol and z>=p["rim_z"]-lr-tol:
            error=abs(math.hypot(r-(pr-lr),z-(p["rim_z"]-lr))-lr)
            if error<tol:
                rim_points.append(error)
    assert len(rim_points)>int(p["count"]), "Round lip arc missing"
    # Measure the actual side silhouette: three R3 shoulder heights and the lip.
    hw=p["band_w"]/2
    rise=p["rim_z"]-p["lip_h"]-p["ring_r"]
    runout=pr-hw
    length=math.hypot(runout,rise)
    ux=runout/length; uz=rise/length
    straight=abs(runout)<tol
    tangent=0 if straight else p["shoulder_r"]*(1-uz)/ux
    z0=p["ring_r"]-tangent
    z1=p["ring_r"]+tangent*uz
    shoulder_probes=[]
    for fraction in (0.25,0.5,0.75):
        z=z0+(rise if straight else z1-z0)*fraction
        expected_y=hw if straight else hw+p["shoulder_r"]-math.sqrt(p["shoulder_r"]**2-(z-z0)**2)
        actual=hit((0,pr+p["probe"],z),(0,-1,0))[1]
        assert abs(actual-expected_y)<tol,(z,actual,expected_y)
        shoulder_probes.append({"z_cm":z,"measured_y_cm":actual,"expected_y_cm":expected_y})
    z=p["rim_z"]-lr/2
    expected_y=pr-lr+math.sqrt(lr**2-(lr/2)**2)
    actual=hit((0,pr+p["probe"],z),(0,-1,0))[1]
    assert abs(actual-expected_y)<tol,(actual,expected_y)
    land=float(obj["top_land_cm"])
    assert land>=p["min_land"]-tol,(land,p["min_land"])
    points=[(r["x_cm"],r["y_cm"]) for r in records]
    min_gap=min(math.dist(a,b)-p["pit_d"] for i,a in enumerate(points) for b in points[i+1:])
    edge_gap=p["bowl_d"]/2-p["array_radius"]-p["pit_d"]/2
    assert min_gap>0 and edge_gap>0
    report={"object":obj.name,"blender_version":bpy.app.version_string,"units":"cm","bbox":box,"expected_size_cm":expected,"topology":topo,"connected_components":len(components),"volume_cm3":volume,"bore_diameter_cm":bore,"central_floor_thickness_cm":core,"pits":measured_pits,"top_flat_land_cm":land,"round_lip_arc_vertices":len(rim_points),"shoulder_probes":shoulder_probes,"round_lip_probe":{"z_cm":z,"measured_y_cm":actual,"expected_y_cm":expected_y},"pit_gap_cm":min_gap,"pit_to_nominal_bowl_edge_cm":edge_gap,"tolerance_cm":tol,"physical_fit_and_strength":"not tested"}
    path=os.path.join(ctx.proj_dir,"spec","verification_report.json")
    report["ring_support_end_fillet"]=junction
    report["shoulder_profile"]="straight aligned wall" if straight else "R3 fillet and slope"
    # Measure the band where the end-round leaves a flat annular face.
    z_band=-(p["bore_d"]/2+p["ring_r"])/2
    y_plus=hit((0,hw+p["probe"],z_band),(0,-1,0))[1]
    y_minus=hit((0,-hw-p["probe"],z_band),(0,1,0))[1]
    report["band_width_cm"]=y_plus-y_minus
    assert abs(report["band_width_cm"]-p["band_w"])<tol,report["band_width_cm"]
    with open(path,"w",encoding="utf-8") as f:
        json.dump(report,f,ensure_ascii=False,indent=2)
    print("VERIFIED",json.dumps(report,ensure_ascii=False))
