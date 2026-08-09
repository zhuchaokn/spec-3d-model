"""make_box.py — 创建一个命名长方体（cuboid）。

幂等：创建前先删同名对象，重跑安全。
可调参数见下方常量，改完用 execute_blender_code(file_path=__file__) 跑。
输出：print "OK created <NAME> dimensions=... at ..."（addon 把 stdout 返回调用方）。
"""
import bpy

# ---- params (edit me) ----
NAME = "MyBox"
SIZE = 1.0                       # 基础立方体边长，最终尺寸由 DIMENSIONS 决定
DIMENSIONS = (2.0, 3.0, 1.5)    # 最终 (x, y, z) 尺寸（Blender 单位）
LOCATION = (0.0, 0.0, 1.0)
# --------------------------

for obj in list(bpy.data.objects):
    if obj.name == NAME:
        bpy.data.objects.remove(obj, do_unlink=True)

bpy.ops.mesh.primitive_cube_add(size=SIZE, location=LOCATION)
box = bpy.context.active_object
box.name = NAME
box.scale = DIMENSIONS
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

print(f"OK created {NAME} dimensions={tuple(round(d, 3) for d in box.dimensions)} at {tuple(round(c, 3) for c in box.location)}")
