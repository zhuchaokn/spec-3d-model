"""op: hex_array — 对 target(半筐)四壁+底铺 pointy-top 六边形并布尔减(镂空)。

方案A 的"生成器节点":一个节点展开成 N 个六边形 cutter,合并后一次布尔。
读 target 的包围盒得到该半的实际范围,按 params 在每个面上铺规则六边形网格,
跳过:切缝禁孔带、把手矩形、凹沿 profile 上方。铺算逻辑全在此(与业务几何相关,
属 op 层,不进纯调度引擎)。

ctx.targets: 被镂空的半筐(读其 bbox 定范围)。
ctx.params:
  hex_w, gap, wall
  margin_side, margin_bottom, margin_top, margin_bottom_face(底板留边)
  seam_side: '+x'/'-x' —— 缝在哪侧(该侧短墙=开口,不打孔;另一短墙打)
  seam_half: 缝禁孔带半宽(长墙+底板缝侧此范围不打孔)
  handle: [w,h,gap_top] 短墙把手矩形(该矩形区不打孔),或 null
  scallop: [dip,corner,flat] 长墙凹沿(高于 profile 的孔跳过),或 null
"""
from math import floor, sqrt
import bmesh
import bpy
import s3d

SQRT3 = sqrt(3.0)


def run(ctx):
    p = ctx.params
    tgt = None
    for d in ctx.targets.values():
        tgt = d["object"]
    if tgt is None:
        raise ValueError(f"hex_array {ctx.name}: target 不存在")

    bb = s3d.bbox(tgt.name)
    x0, y0, z0 = bb["min"]
    x1, y1, z1 = bb["max"]
    L = x1 - x0          # 该半沿 X 长
    W = y1 - y0          # Y 宽(=全宽)
    H = z1 - z0          # 高

    hex_w = p["hex_w"]; gap = p["gap"]; wall = p["wall"]
    ms = p["margin_side"]; mb = p["margin_bottom"]; mt = p["margin_top"]
    mbf = p.get("margin_bottom_face", mb)
    seam_side = p.get("seam_side", "+x")
    seam_half = p.get("seam_half", 0.0)
    handle = p.get("handle")            # [w,h,gap_top] or None
    scallop = p.get("scallop")          # [dip,corner,flat] or None

    R = hex_w / SQRT3
    HH = hex_w / 2
    hex_h = 2 * R
    dx = hex_w + gap
    dy = 0.75 * hex_h + gap

    # 缝的绝对 X 坐标(不打孔那侧)。seam_side '+x' → 缝在 x1;短墙开口在 x1,打 x0 墙
    seam_x = x1 if seam_side == "+x" else x0

    full_L = p["full_L"]     # 整筐全长(凹沿 profile 关于缝 x=0 对称定义)

    def profile_z(x_abs):
        """长墙凹沿后上沿绝对高度。x_abs 为绝对 X(缝在 x=0)。scallop=None→平顶。"""
        if not scallop:
            return z0 + H
        dip, corner, flat = scallop
        mid_half = full_L / 2 - corner
        dip_z = (z0 + H) - dip
        ax = abs(x_abs)
        if ax <= flat:
            return dip_z
        if ax >= mid_half:
            return z0 + H
        t = (ax - flat) / (mid_half - flat)
        return dip_z + t * dip

    def hits_handle(u, v):
        if not handle:
            return False
        hw, hh, gtop = handle
        z_hi = (z0 + H) - gtop
        z_lo = z_hi - hh
        return (u - HH < hw/2 and u + HH > -hw/2 and v - R < z_hi and v + R > z_lo)

    cutters = []

    def tile_rect(along0, along1, up0, up1, place_fn,
                  seam_clear_abs=None, use_profile=False, skip_handle=False):
        """在 [along0,along1]×[up0,up1] 铺六边形,place_fn(u_center,v_center)->建cutter。"""
        aspan = along1 - along0
        uspan = up1 - up0
        nv = 0 if uspan < 0.75*hex_h else int(floor((uspan + gap) / (dy)))
        if nv > 0 and nv % 2 == 0:
            nv -= 1
        nv = max(nv, 1)
        v_first = up0 + (uspan - (nv - 1) * dy) / 2
        acenter = (along0 + along1) / 2
        for r in range(nv):
            vc = v_first + r * dy
            off = 0.0 if (r % 2 == 0) else dx / 2
            m = 0
            while m <= 200:
                cands = [0.0] if (off == 0 and m == 0) else [off + m*dx, -(off + m*dx)]
                any_in = False
                for c in cands:
                    uc = acenter + c
                    if uc - HH < along0 or uc + HH > along1:
                        continue
                    any_in = True
                    if seam_clear_abs is not None and abs(uc - seam_clear_abs) - HH < seam_half:
                        continue
                    if use_profile and vc + R > profile_z(uc):
                        continue
                    if skip_handle and hits_handle(uc, vc):
                        continue
                    place_fn(uc, vc)
                if not any_in and m > 0:
                    break
                m += 1

    def make_hex(orient, face_pos, cu, cv):
        R2 = R
        pts = [(0.0, R2), (HH, R2/2), (HH, -R2/2), (0.0, -R2), (-HH, -R2/2), (-HH, R2/2)]
        name = f"_hex_{len(cutters)}"
        c = s3d.prism(name, pts, orient, face_pos, cu, cv, 2.5*wall)
        cutters.append(c)

    up_lo = z0 + wall + mb
    up_hi = z0 + H - mt

    # 前墙(+Y)/后墙(−Y):along=X,use profile + seam clear
    for fp in (y1, y0):
        tile_rect(x0 + ms, x1 - ms, up_lo, up_hi,
                  lambda u, v, fp=fp: make_hex('wall_y', fp, u, v),
                  seam_clear_abs=seam_x, use_profile=bool(scallop))
    # 外短墙(远离缝那侧):along=Y,skip handle
    outer_x = x0 if seam_side == "+x" else x1
    tile_rect(y0 + ms, y1 - ms, up_lo, up_hi,
              lambda u, v: make_hex('wall_x', outer_x, u, v),
              skip_handle=bool(handle))
    # 底板:along=X,up=Y,seam clear
    tile_rect(x0 + mbf, x1 - mbf, y0 + mbf, y1 - mbf,
              lambda u, v: make_hex('bottom', z0 + wall/2, u, v),
              seam_clear_abs=seam_x)

    if cutters:
        s3d.bool_diff_many(tgt, cutters)
    print(f"  [hex_array] {ctx.name} holes={len(cutters)} on {tgt.name}")
