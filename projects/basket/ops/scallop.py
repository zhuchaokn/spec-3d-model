"""op: scallop — 对 target 前后长墙上沿切出 \\___/ 凹沿。

切割器 = X-Z 平面梯形(上宽下窄:两端满高、中间凹下),沿 Y 拉伸穿过前后墙。
对某半筐做布尔减时,梯形关于缝(x=0)对称,该半只与自己那侧相交 → 自然裁出半个凹沿,
四角(|x|≥mid_half)无切割器 → 保持满高。

ctx.center: 锚点(缝 x=0, y=0 居中, z=0 地面)。
ctx.params: L(全长,定义 profile), W(全宽,定 Y 拉伸深), H, dip, corner, flat, over。
"""
import bmesh
import bpy
import s3d


def run(ctx):
    p = ctx.params
    L, W, H = p["L"], p["W"], p["H"]
    dip, corner, flat, over = p["dip"], p["corner"], p["flat"], p["over"]
    cx, cy, cz = ctx.center
    mid_half = L / 2 - corner
    dip_z = H - dip
    top_z = H + over
    # 梯形 (X,Z),相对锚点:上边 ±mid_half@top_z,下边 ±flat@dip_z
    pts = [(-mid_half, top_z), (mid_half, top_z), (flat, dip_z), (-flat, dip_z)]
    depth = (W + 2.0) * s3d.CM          # Y 方向拉伸,超出全宽以穿透前后墙
    CM = s3d.CM
    tmp = f"_cut_{ctx.name}"
    s3d.clean_by_names(names=(tmp,))

    bm = bmesh.new()
    back = [bm.verts.new(((cx + u) * CM, cy * CM - depth / 2, (cz + v) * CM)) for (u, v) in pts]
    front = [bm.verts.new(((cx + u) * CM, cy * CM + depth / 2, (cz + v) * CM)) for (u, v) in pts]
    bm.faces.new(back)
    bm.faces.new(list(reversed(front)))
    n = len(pts)
    for i in range(n):
        bm.faces.new((back[i], back[(i+1) % n], front[(i+1) % n], front[i]))
    bm.normal_update()
    me = bpy.data.meshes.new(tmp)
    bm.to_mesh(me); bm.free()
    cutter = bpy.data.objects.new(tmp, me)
    bpy.context.collection.objects.link(cutter)

    tnames = []
    for dep in ctx.targets.values():
        if dep["object"] is None:
            raise ValueError(f"scallop {ctx.name}: target 不存在")
        s3d.bool_diff(dep["object"], cutter, apply=True, remove_cutter=False)
        tnames.append(dep["object"].name)
    s3d.clean_by_names(names=(tmp,))
    print(f"  [scallop] {ctx.name} dip={dip} from {tnames}")
