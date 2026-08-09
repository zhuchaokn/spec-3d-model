"""make_basket.py — 蜂巢镂空筐：四壁+底部六边形孔、长边凹沿、两侧胶囊把手、敞口。

要点：
- 六边形 pointy-top（尖顶朝上，无平桥，FDM 竖直打无塌陷）。
- 边缘咬边：六边形跨过筐壁边缘、被自然裁切成半hex，左右两边镜像对称、不参差。
- 奇数行：nv 强制奇数并垂直居中，上下对称。
- 长边(前/后墙)上边做成 \\——/ 凹沿（两端高、中间低），省料+便于查看；凹沿区内高于profile的孔跳过。
- 四面孔同尺寸(HEX_W 统一)。
墙厚3mm。幂等：重跑先删 Basket / Cutter*。
实现：外壳 - 内腔 - 六边形孔(合并布尔) - 长边凹沿(单独布尔) - 两侧胶囊把手(单独布尔)。
     孔/凹沿/把手均 bmesh 流形棱柱。
参数见下方常量，改完用 execute_blender_code(file_path=__file__) 跑。
"""
import bpy
import bmesh
from math import floor, pi, cos, sin, sqrt

# ---- params (edit me) ----
LENGTH = 29.0
WIDTH = 20.0
HEIGHT = 20.0
WALL = 0.3
HEX_W = 2.5           # 六边形孔宽(平边到平边) cm —— 四面统一
HEX_GAP = 0.7         # 孔间距(孔间墙网) cm
MARGIN_SIDE = 1.0
MARGIN_BOTTOM = 1.2
MARGIN_TOP = 1.0
BOTTOM_MARGIN = 1.0
# 长边凹沿
SCALLOP_DIP = 5.0     # 中间凹下深度 cm
SCALLOP_CORNER = 4.0  # 两端满高段长 cm
SCALLOP_FLAT = 6.0    # 中间平底半宽 cm
SCALLOP_OVER = 1.0    # 凹沿切割器顶部超出墙顶量 cm（防止与墙顶共面留残边）
# 把手
HANDLE_W = 8.0
HANDLE_H = 4.0
HANDLE_GAP_TOP = 3.0
BEVEL = 0.04
# 竖向分割 + 圆柱C夹卡合（P2S 25cm 打印区）
SPLIT = True          # True=中心X=0竖切成BasketL/BasketR并加卡合；False=保持整体单件
SEAM_HALF = 0.75      # 切缝禁孔半宽 cm：前后墙+底板此范围内不打孔，留实体接卡夹
JOINT_OD = 0.90       # C夹墩外径 φ9mm
JOINT_ID = 0.512      # C夹内孔 φ5.12mm（滑动基准孔）
PIN_OD = 0.50         # pin柱身 φ5.0mm（<孔→微涩滑动）
PIN_OD_BOT = 0.512    # pin柱底 φ5.12mm（=孔→到底过盈卡住防Z脱）
PIN_BOT_H = 0.6       # pin柱底涨径段高度 cm
SLOT_W = 0.32         # C夹开口缝宽 cm（略>墙厚0.3，让颈滑动）
JOINT_TOP = 15.0      # 卡合柱顶高 cm（=dip_z凹沿最低点，勿凸进凹口）
SPLIT_SHOW_GAP = 4.0  # 两半展示间距(各挪X) cm；仅便于查看，导出前可设0
CYL_SEG = 64          # 圆柱分段
# --------------------------

M = 1.0 / 100.0
_SQRT3 = sqrt(3.0)


def _sel(obj, only=True):
    if only:
        bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def add_box(name, size_cm, loc_cm=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=tuple(v * M for v in loc_cm))
    o = bpy.context.active_object
    o.name = name
    o.scale = tuple(v * M for v in size_cm)
    _sel(o)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return o


def bool_diff(target, cutter, name="Bool"):
    _sel(target)
    mod = target.modifiers.new(name, 'BOOLEAN')
    mod.object = cutter
    mod.operation = 'DIFFERENCE'
    mod.solver = 'EXACT'
    bpy.ops.object.modifier_apply(modifier=mod.name)


def _prism(name, pts_uv, orient, face_pos, cu, cv, depth, v_center):
    """通用流形棱柱：pts_uv=2D轮廓(u,v)cm；orient: 'wall_y'(法Y/沿X/上Z) 'wall_x'(法X/沿Y/上Z) 'bottom'(法Z/沿X/上Y)。
    cu,cv=沿/上 中心；depth=法向厚度cm；v_center=轮廓v的居中偏移。"""
    def w(u, v, t):
        au, av = u, v - v_center
        if orient == 'wall_y':
            return ((cu + au) * M, (face_pos + t) * M, (cv + av) * M)
        if orient == 'wall_x':
            return ((face_pos + t) * M, (cu + au) * M, (cv + av) * M)
        return ((cu + au) * M, (cv + av) * M, (face_pos + t) * M)

    n = len(pts_uv)
    bm = bmesh.new()
    back = [bm.verts.new(w(u, v, -depth / 2)) for (u, v) in pts_uv]
    front = [bm.verts.new(w(u, v, depth / 2)) for (u, v) in pts_uv]
    bm.faces.new(back)
    bm.faces.new(list(reversed(front)))
    for i in range(n):
        bm.faces.new((back[i], back[(i + 1) % n], front[(i + 1) % n], front[i]))
    bm.normal_update()
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(obj)
    return obj


def make_hex(name, orient, face_pos, cu, cv):
    R = HEX_W / _SQRT3
    h = R * _SQRT3 / 2
    pts = [(0.0, R), (h, R / 2), (h, -R / 2), (0.0, -R), (-h, -R / 2), (-h, R / 2)]
    return _prism(name, pts, orient, face_pos, cu, cv, 2.5 * WALL, v_center=0.0)


def make_capsule(name, length_m, height_m, depth_m, loc_m, seg=24):
    r = height_m / 2
    sr = length_m / 2 - r
    perim = []
    for i in range(seg + 1):
        a = -pi / 2 + pi * i / seg
        perim.append((sr + r * cos(a), r * sin(a)))
    perim.append((-sr, r))
    for i in range(1, seg + 1):
        a = pi / 2 + pi * i / seg
        perim.append((-sr + r * cos(a), r * sin(a)))
    n = len(perim)
    bm = bmesh.new()
    back = [bm.verts.new((-depth_m / 2, y, z)) for (y, z) in perim]
    front = [bm.verts.new((depth_m / 2, y, z)) for (y, z) in perim]
    bm.faces.new(back)
    bm.faces.new(list(reversed(front)))
    for i in range(n):
        bm.faces.new((back[i], back[(i + 1) % n], front[(i + 1) % n], front[i]))
    bm.normal_update()
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    obj.location = loc_m
    bpy.context.collection.objects.link(obj)
    return obj


def add_cylinder(name, dia_cm, h_cm, loc_cm):
    """竖直圆柱(轴=Z)，直径/高/位置单位 cm。"""
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=CYL_SEG, radius=dia_cm / 2 * M, depth=h_cm * M,
        location=tuple(v * M for v in loc_cm))
    o = bpy.context.active_object
    o.name = name
    return o


def _join_objs(target, others):
    bpy.ops.object.select_all(action='DESELECT')
    for o in others:
        o.select_set(True)
    target.select_set(True)
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.join()


def _seam_y_axis(face_pos):
    """卡合柱轴的 Y 坐标：墩外缘贴住该墙内表面，墩体伸向腔内。"""
    inner = face_pos - (T_SIGN(face_pos)) * WALL  # 墙内表面 Y
    return inner - T_SIGN(face_pos) * (JOINT_OD / 2)


def T_SIGN(v):
    return 1.0 if v >= 0 else -1.0


def make_cclip(basket, face_pos):
    """在 basket 上、face_pos 墙的切缝端造 C 夹(φJOINT_OD墩+φJOINT_ID孔+朝+X缝)，join 进 basket。"""
    ya = _seam_y_axis(face_pos)
    zc = (WALL + JOINT_TOP) / 2
    h = JOINT_TOP - WALL
    xa = -SEAM_HALF + JOINT_OD / 2  # 墩体落在左半(X<0)一侧、贴近切缝
    post = add_cylinder("SeamPost", JOINT_OD, h, (xa, ya, zc))
    hole = add_cylinder("SeamHole", JOINT_ID, h + 1.0, (xa, ya, zc))
    bool_diff(post, hole)
    # 开缝：朝 +X 通到墩外，缝宽 SLOT_W，Z 向贯通
    _sel(post)
    slot = add_box("SeamSlot", (JOINT_OD, SLOT_W, h + 1.0), (xa + JOINT_OD / 2, ya, zc))
    bool_diff(post, slot)
    _join_objs(basket, [post])


def make_pin(basket, face_pos):
    """在 basket 上、face_pos 墙的切缝端造 pin(φPIN_OD柱身+φPIN_OD_BOT涨底)，与对面C夹孔同轴，join 进 basket。"""
    ya = _seam_y_axis(face_pos)
    xa = -SEAM_HALF + JOINT_OD / 2  # 与 C 夹孔同轴(同一 X/Y)
    body_h = JOINT_TOP - WALL - PIN_BOT_H
    bot_zc = WALL + PIN_BOT_H / 2
    body_zc = WALL + PIN_BOT_H + body_h / 2
    bot = add_cylinder("SeamPinBot", PIN_OD_BOT, PIN_BOT_H, (xa, ya, bot_zc))
    body = add_cylinder("SeamPin", PIN_OD, body_h, (xa, ya, body_zc))
    _join_objs(body, [bot])
    _join_objs(basket, [body])


def make_scallop(name, face_pos):
    """长边凹沿切割器：X-Z 梯形(上宽下窄)，沿Y拉伸。去掉 profile..H 的边沿材料。"""
    mid_half = LENGTH / 2 - SCALLOP_CORNER
    dip_z = HEIGHT - SCALLOP_DIP
    top_z = HEIGHT + SCALLOP_OVER  # 抬出墙顶，避免共面残边
    pts = [(-mid_half, top_z), (mid_half, top_z),
           (SCALLOP_FLAT, dip_z), (-SCALLOP_FLAT, dip_z)]  # (X, Z)
    depth = 2.5 * WALL

    def w(x, z, t):  # wall_y: X=x, Y=face_pos+t, Z=z
        return (x * M, (face_pos + t) * M, z * M)

    n = len(pts)
    bm = bmesh.new()
    back = [bm.verts.new(w(x, z, -depth / 2)) for (x, z) in pts]
    front = [bm.verts.new(w(x, z, depth / 2)) for (x, z) in pts]
    bm.faces.new(back)
    bm.faces.new(list(reversed(front)))
    for i in range(n):
        bm.faces.new((back[i], back[(i + 1) % n], front[(i + 1) % n], front[i]))
    bm.normal_update()
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(obj)
    return obj


def profile_z(x):
    """长边凹沿后的上沿高度（前/后墙）。"""
    mid_half = LENGTH / 2 - SCALLOP_CORNER
    dip_z = HEIGHT - SCALLOP_DIP
    ax = abs(x)
    if ax <= SCALLOP_FLAT:
        return dip_z
    if ax >= mid_half:
        return HEIGHT
    t = (ax - SCALLOP_FLAT) / (mid_half - SCALLOP_FLAT)
    return dip_z + t * SCALLOP_DIP


def grid_count(span, hole, gap):
    return 0 if span < hole else int(floor((span + gap) / (hole + gap)))


def _handle_rect():
    return (-HANDLE_W / 2, HANDLE_W / 2), (HEIGHT - HANDLE_GAP_TOP - HANDLE_H, HEIGHT - HANDLE_GAP_TOP)


def _hex_overlaps_handle(uc, vc):
    (hy0, hy1), (hz0, hz1) = _handle_rect()
    hw = HEX_W / 2
    hh = HEX_W / _SQRT3
    return (uc - hw < hy1 and uc + hw > hy0 and vc - hh < hz1 and vc + hh > hz0)


def row_centers(r, along_span, dx):
    """对称外扩生成一行六边形中心：偶行 hex@0 然后 ±m*dx；奇行 ±(m+0.5)dx。
    跨过边缘的也放(被筐壁裁切成半hex)，直到两侧都超出边沿+冗余。"""
    off = 0.0 if (r % 2 == 0) else dx / 2
    centers = []
    m = 0
    while True:
        cand = [0.0] if (off == 0 and m == 0) else [off + m * dx, -(off + m * dx)]
        any_in = False
        for c in cand:
            if abs(c) + HEX_W / 2 <= along_span / 2:  # 孔整体落在镂空区内，不咬边（四角留实体柱）
                centers.append(c)
                any_in = True
        if not any_in and m > 0:
            break
        m += 1
        if m > 100:
            break
    return centers


def main():
    for obj in list(bpy.data.objects):
        if (obj.name in ("Basket", "BasketL", "BasketR")
                or obj.name.startswith("Cutter") or obj.name.startswith("Seam")):
            bpy.data.objects.remove(obj, do_unlink=True)

    L, W, H, T = LENGTH, WIDTH, HEIGHT, WALL
    eps = 0.01

    shell = add_box("Basket", (L, W, H), (0, 0, H / 2))
    cav = add_box("CutterCavity",
                  (L - 2 * T + eps, W - 2 * T + eps, H - T + eps),
                  (0, 0, T + (H - T) / 2))
    bool_diff(shell, cav)

    cutters = []
    hex_h = 2 * (HEX_W / _SQRT3)
    R = HEX_W / _SQRT3
    dx = HEX_W + HEX_GAP
    dy = 0.75 * hex_h + HEX_GAP

    def emit_hex(orient, face_pos, along_span, up_low, up_high, skip_handle=False,
                 profile_fn=None, seam_clear=False):
        up_span = up_high - up_low
        nv = grid_count(up_span, 0.75 * hex_h, HEX_GAP)
        if nv > 0 and nv % 2 == 0:
            nv -= 1  # 强制奇数行
        if nv < 1:
            nv = 1
        v_first = up_low + (up_span - (nv - 1) * dy) / 2
        cnt = 0
        for r in range(nv):
            vc = v_first + r * dy
            for uc in row_centers(r, along_span, dx):
                if skip_handle and _hex_overlaps_handle(uc, vc):
                    continue
                if profile_fn and vc + R > profile_fn(uc):
                    continue  # 凹沿区内高于 profile 的孔跳过
                if seam_clear and abs(uc) - HEX_W / 2 < SEAM_HALF:
                    continue  # 切缝禁孔区：留实体接卡夹
                cutters.append(make_hex(f"CutterHex{len(cutters)}", orient, face_pos, uc, vc))
                cnt += 1
        return cnt

    up_low = T + MARGIN_BOTTOM
    up_high = H - MARGIN_TOP
    n_fb = emit_hex('wall_y', W / 2, L - 2 * MARGIN_SIDE, up_low, up_high, profile_fn=profile_z, seam_clear=SPLIT)
    n_fb += emit_hex('wall_y', -W / 2, L - 2 * MARGIN_SIDE, up_low, up_high, profile_fn=profile_z, seam_clear=SPLIT)
    n_lr = emit_hex('wall_x', L / 2, W - 2 * MARGIN_SIDE, up_low, up_high, skip_handle=True)
    n_lr += emit_hex('wall_x', -L / 2, W - 2 * MARGIN_SIDE, up_low, up_high, skip_handle=True)
    n_bot = emit_hex('bottom', T / 2, L - 2 * BOTTOM_MARGIN,
                     -(W - 2 * BOTTOM_MARGIN) / 2, (W - 2 * BOTTOM_MARGIN) / 2, seam_clear=SPLIT)

    # 六边形孔：合并后一次布尔
    if cutters:
        bpy.ops.object.select_all(action='DESELECT')
        for c in cutters:
            c.select_set(True)
        bpy.context.view_layer.objects.active = cutters[0]
        bpy.ops.object.join()
        joined = bpy.context.active_object
        joined.name = "CutterHexes"
        bool_diff(shell, joined)
        bpy.data.objects.remove(joined, do_unlink=True)

    if "CutterCavity" in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects["CutterCavity"], do_unlink=True)

    # 长边凹沿：前/后墙单独布尔
    scallop_cnt = 0
    for face_pos in (W / 2, -W / 2):
        sc = make_scallop(f"CutterScallop_{scallop_cnt}", face_pos)
        bool_diff(shell, sc)
        bpy.data.objects.remove(sc, do_unlink=True)
        scallop_cnt += 1

    # 两侧胶囊把手：单独布尔
    hzc = H - HANDLE_GAP_TOP - HANDLE_H / 2
    depth = 2.5 * T
    handle_cnt = 0
    for face_x in (L / 2, -L / 2):
        hc = make_capsule(f"CutterHandle_{handle_cnt}",
                          HANDLE_W * M, HANDLE_H * M, depth * M,
                          (face_x * M, 0, hzc * M))
        bool_diff(shell, hc)
        bpy.data.objects.remove(hc, do_unlink=True)
        handle_cnt += 1

    shell.name = "Basket"

    if BEVEL > 0:
        try:
            _sel(shell)
            bv = shell.modifiers.new("Bevel", 'BEVEL')
            bv.width = BEVEL * M
            bv.segments = 2
            bpy.ops.object.modifier_apply(modifier=bv.name)
        except Exception as e:
            print(f"(bevel skipped: {e})")

    us = bpy.context.scene.unit_settings
    us.system = 'METRIC'
    us.length_unit = 'CENTIMETERS'

    if not SPLIT:
        _sel(shell)
        print(f"OK created Basket outer={LENGTH}x{WIDTH}x{HEIGHT}cm wall={WALL}cm "
              f"hex_holes={n_fb + n_lr + n_bot} (fb={n_fb} lr={n_lr} bottom={n_bot}) "
              f"scallop={scallop_cnt} handles={handle_cnt}({HANDLE_W}x{HANDLE_H}cm) "
              f"hex_rows=odd/centered, edge=half-hex")
        return

    # ---- 竖向分割 + 圆柱C夹卡合 ----
    big = max(L, W, H) * 3
    gap = 0.015  # 切面让位 0.15mm

    # 先复制出右半原胚，再各自切
    right = shell.copy()
    right.data = shell.data.copy()
    bpy.context.collection.objects.link(right)
    left = shell
    left.name = "BasketL"
    right.name = "BasketR"

    # 左半：切掉 X > +gap/2
    cutL = add_box("CutterSplitL", (big, big, big), (big / 2 + gap / 2, 0, H / 2))
    bool_diff(left, cutL)
    # 右半：切掉 X < -gap/2
    cutR = add_box("CutterSplitR", (big, big, big), (-big / 2 - gap / 2, 0, H / 2))
    bool_diff(right, cutR)

    # 前后墙各一套：左半C夹 + 右半pin
    for face_pos in (W / 2, -W / 2):
        make_cclip(left, face_pos)
        make_pin(right, face_pos)

    # 展示间距：两半沿 X 分开便于查看
    left.location.x -= SPLIT_SHOW_GAP * M
    right.location.x += SPLIT_SHOW_GAP * M

    _sel(left)
    print(f"OK split BasketL/BasketR seam=X0 "
          f"cclip(OD={JOINT_OD*10}mm ID={JOINT_ID*10}mm slot={SLOT_W*10}mm) "
          f"pin(body={PIN_OD*10}mm bot={PIN_OD_BOT*10}mm) clips=前后各1 "
          f"hex_holes={n_fb + n_lr + n_bot} show_gap={SPLIT_SHOW_GAP}cm")


main()
