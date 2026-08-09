"""make_clip_tester.py — C夹 + 抱柱 松紧度试印件（各带底座，独立两件）。

用途：整筐分割前，先单独打这套小件试配合松紧，定下最终孔/柱尺寸。
两件：
- ClipTester：φJOINT_OD 实心竖墩 + 中心 φJOINT_ID 竖直通孔 + 朝 +X 开 SLOT_W 缝 → C 形夹，带方底座。
- PinTester：φPIN_OD 柱身 + 底部 PIN_BOT_H 段涨到 φPIN_OD_BOT（过盈）→ 抱柱，带方底座。
配合：抱柱沿 Z 从顶滑入 C 夹孔。柱身 PIN_OD < 孔 JOINT_ID → 微涩滑动；
      柱底 PIN_OD_BOT = 孔径 → 到底涨紧卡住，防 Z 向脱落。
孔轴 = Z（竖直），便于平放打印、层线绕柱、臂根较强。
两件沿 X 分开摆放，各自独立可拿。
幂等：重跑先删 ClipTester/PinTester/ClipTesterBase/PinTesterBase/CT_*。自包含。末尾 print。
参数见下方常量，改完用 execute_blender_code(file_path=__file__) 跑。
"""
import bpy
import bmesh
from math import pi

# ---- params (edit me) ----
CLIP_H = 2.0          # C夹 / 抱柱有效高度 cm
JOINT_OD = 0.90       # C夹墩外径 φ9mm
JOINT_ID = 0.512      # C夹内孔 φ5.12mm（滑动配合基准孔）
PIN_OD = 0.50         # 抱柱柱身 φ5.0mm（< 孔 → 微涩滑动）
PIN_OD_BOT = 0.512    # 抱柱底部 φ5.12mm（= 孔 → 到底过盈卡住）
PIN_BOT_H = 0.6       # 柱底涨径段高度 cm
SLOT_W = 0.30         # C夹开口缝宽 = 墙厚 3mm
WALL_T = 0.30         # 模拟墙片厚 3mm（= 颈厚，穿过 C 夹缝）
WALL_EXT = 1.2        # 墙片伸出长度 cm
BASE_L = 1.3          # 底座长(偏置方向) cm
BASE_W = 1.0          # 底座宽 cm
BASE_H = 0.25         # 底座厚 cm
BASE_OFF = 0.75       # 底座中心相对柱心的偏移 cm（偏到柱外侧，空出柱间通道以便对插）
GAP_X = 4.0           # 两件中心 X 间距 cm
CYL_SEG = 64          # 圆柱分段（越大越圆）
# --------------------------

M = 1.0 / 100.0
NAMES = ("ClipTester", "PinTester", "ClipTesterBase", "PinTesterBase")


def _clean():
    for obj in list(bpy.data.objects):
        if obj.name in NAMES or obj.name.startswith("CT_"):
            bpy.data.objects.remove(obj, do_unlink=True)


def _sel(obj):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def add_cylinder(name, dia_cm, h_cm, loc_cm):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=CYL_SEG, radius=dia_cm / 2 * M, depth=h_cm * M,
        location=tuple(v * M for v in loc_cm))
    o = bpy.context.active_object
    o.name = name
    return o


def add_box(name, size_cm, loc_cm):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=tuple(v * M for v in loc_cm))
    o = bpy.context.active_object
    o.name = name
    o.scale = tuple(v * M for v in size_cm)
    _sel(o)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return o


def bool_diff(target, cutter):
    _sel(target)
    mod = target.modifiers.new("Bool", 'BOOLEAN')
    mod.object = cutter
    mod.operation = 'DIFFERENCE'
    mod.solver = 'EXACT'
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cutter, do_unlink=True)


def join_into(target, others):
    bpy.ops.object.select_all(action='DESELECT')
    for o in others:
        o.select_set(True)
    target.select_set(True)
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.join()


def make_clip(cx):
    """C夹：底座(偏置到-X外侧) + 实心墩挖通孔 + 开缝。孔轴=Z。返回主对象。"""
    base_z = BASE_H / 2
    post_z = BASE_H + CLIP_H / 2
    base = add_box("ClipTesterBase", (BASE_L, BASE_W, BASE_H), (cx - BASE_OFF, 0, base_z))
    post = add_cylinder("ClipTester", JOINT_OD, CLIP_H, (cx, 0, post_z))
    # 中心通孔（穿透墩+底座，多留余量）
    hole = add_cylinder("CT_hole", JOINT_ID, CLIP_H + BASE_H + 1.0, (cx, 0, post_z))
    bool_diff(post, hole)
    # 开缝：朝 +X，从孔通到墩外，缝宽 SLOT_W，穿透整高
    slot = add_box("CT_slot", (JOINT_OD, SLOT_W, CLIP_H + 1.0),
                   (cx + JOINT_OD / 2, 0, post_z))
    bool_diff(post, slot)
    # 模拟墙片（代表左半墙）：朝 -X 伸出，与墩背面(缝对侧)相连
    wall = add_box("CT_wallL", (WALL_EXT, WALL_T, CLIP_H),
                   (cx - JOINT_OD / 2 - WALL_EXT / 2 + 0.1, 0, post_z))
    join_into(post, [base, wall])
    post.name = "ClipTester"
    return post


def make_pin(cx):
    """抱柱：底座 + 柱身 + 底部涨径段。返回主对象。"""
    base_z = BASE_H / 2
    body_h = CLIP_H - PIN_BOT_H
    bot_z = BASE_H + PIN_BOT_H / 2
    body_z = BASE_H + PIN_BOT_H + body_h / 2
    base = add_box("PinTesterBase", (BASE_L, BASE_W, BASE_H), (cx + BASE_OFF, 0, base_z))
    bot = add_cylinder("CT_pinbot", PIN_OD_BOT, PIN_BOT_H, (cx, 0, bot_z))
    body = add_cylinder("PinTester", PIN_OD, body_h, (cx, 0, body_z))
    # 颈+模拟墙片（代表右半墙）：3mm 厚薄片从柱身朝 +X 伸出(与C夹缝同向,滑入时穿缝)
    post_z = BASE_H + CLIP_H / 2
    wall = add_box("CT_wallR", (WALL_EXT, WALL_T, CLIP_H),
                   (cx + PIN_OD / 2 + WALL_EXT / 2 - 0.1, 0, post_z))
    join_into(body, [base, bot, wall])
    body.name = "PinTester"
    return body


def main():
    _clean()
    clip = make_clip(-GAP_X / 2)
    pin = make_pin(GAP_X / 2)

    us = bpy.context.scene.unit_settings
    us.system = 'METRIC'
    us.length_unit = 'CENTIMETERS'

    _sel(clip)
    print(f"OK clip_tester: ClipTester(OD={JOINT_OD*10}mm ID={JOINT_ID*10}mm slot={SLOT_W*10}mm) "
          f"PinTester(body={PIN_OD*10}mm bot={PIN_OD_BOT*10}mm botH={PIN_BOT_H}cm) "
          f"H={CLIP_H}cm base={BASE_L}x{BASE_W}x{BASE_H}cm off={BASE_OFF}cm gap_x={GAP_X}cm")


main()
