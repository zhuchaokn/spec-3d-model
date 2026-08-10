"""op: scallop — 对 target 前后长墙上沿切出 \\___/ 凹沿(转折可圆角)。

切割器 = X-Z 平面梯形(上宽下窄:两端满高、中间凹下),沿 Y 拉伸穿过前后墙。
对某半筐做布尔减时,梯形关于缝(x=0)对称,该半只与自己那侧相交 → 自然裁出半个凹沿,
四角(|x|≥mid_half)无切割器 → 保持满高。

ctx.center: 锚点(缝 x=0, y=0 居中, z=0 地面)。
ctx.params: L, W, H, dip, corner, flat, over;可选 r_scallop(凹底转折圆角半径)、seg。
"""
import s3d


def run(ctx):
    p = ctx.params
    L, W, H = p["L"], p["W"], p["H"]
    dip, corner, flat, over = p["dip"], p["corner"], p["flat"], p["over"]
    r_scallop = p.get("r_scallop", 0.0)
    seg = int(p.get("seg", 12))
    cx, cy, cz = ctx.center
    mid_half = L / 2 - corner
    dip_z = H - dip
    top_z = H + over
    # 梯形 (X,Z),相对锚点:上边 ±mid_half@top_z,下边 ±flat@dip_z
    pts = [(-mid_half, top_z), (mid_half, top_z), (flat, dip_z), (-flat, dip_z)]
    # 只圆化凹底两个转折点(index 2,3 = ±flat@dip_z),上两角在墙顶之上(被切掉)不必圆
    if r_scallop > 0:
        pts = s3d.round_polygon_2d(pts, r_scallop, seg=seg, only_idx={2, 3})
    depth = W + 2.0                     # Y 拉伸(cm),超出全宽穿透前后墙
    tmp = f"_cut_{ctx.name}"
    s3d.clean_by_names(names=(tmp,))
    # X-Z 平面轮廓、沿 Y 拉伸 = prism 的 'wall_y'(u=X, v=Z, 法向=Y)。prism 内已修法线朝外。
    cutter = s3d.prism(tmp, pts, 'wall_y', cy, cx, cz, depth)

    tnames = []
    for dep in ctx.targets.values():
        if dep["object"] is None:
            raise ValueError(f"scallop {ctx.name}: target 不存在")
        s3d.bool_diff(dep["object"], cutter, apply=True, remove_cutter=False)
        tnames.append(dep["object"].name)
    s3d.clean_by_names(names=(tmp,))
    print(f"  [scallop] {ctx.name} dip={dip} r={r_scallop} from {tnames}")
