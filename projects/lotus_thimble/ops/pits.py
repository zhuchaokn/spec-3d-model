"""Sequential spherical blind dimples, placed on the actual bowl's local height."""
import math
import bpy
import json
import s3d


def run(ctx):
    p=ctx.params
    target=next(iter(ctx.targets.values()))["object"]
    positions=[(0,0)]
    for j in range(int(p["count"])):
        a=2*math.pi*j/p["count"]
        positions.append((p["array_radius"]*math.cos(a),p["array_radius"]*math.sin(a)))
    # A spherical-cap depth sets a radius; hemispheres when diameter=2*depth.
    radius=((p["diameter"]/2)**2+p["depth"]**2)/(2*p["depth"])
    records=[]
    for j,(x,y) in enumerate(positions):
        surface=p["bowl_center_z"]-math.sqrt(p["bowl_r"]**2-x*x-y*y)
        center=(ctx.center[0]+x,ctx.center[1]+y,ctx.center[2]+surface+radius-p["depth"])
        bpy.ops.mesh.primitive_uv_sphere_add(segments=int(p["segments"]),ring_count=int(p["rings"]),radius=radius*s3d.CM,location=tuple(c*s3d.CM for c in center))
        tool=bpy.context.object
        tool.name=f"_NeedlePit{j}"
        s3d.sel(target)
        mod=target.modifiers.new("BlindPit", "BOOLEAN")
        mod.operation="DIFFERENCE"
        mod.solver="MANIFOLD"
        mod.object=tool
        bpy.ops.object.modifier_apply(modifier=mod.name)
        bpy.data.objects.remove(tool,do_unlink=True)
        records.append({"x_cm":x,"y_cm":y,"surface_z_cm":surface,"floor_z_cm":surface-p["depth"]})
    target["needle_pits"]=json.dumps(records)
    print("PITS",len(records),s3d.manifold_report(target.name))
