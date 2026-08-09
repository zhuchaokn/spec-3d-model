"""inspect_object.py — 打印指定对象的网格统计：类型、尺寸、顶点数、面数、位置。

幂等：只读，无副作用。
用途：创建/布尔后验证对象确实生成了预期的几何（如镂空孔会让面数显著升高）。
参数 NAME 指定对象名，改完用 execute_blender_code(file_path=__file__) 跑。
输出：print "<NAME> type=... dims=... verts=... polys=... loc=..."。
"""
import bpy

NAME = "Basket"  # edit me

obj = bpy.data.objects.get(NAME)
if obj is None:
    print(f"NOT_FOUND: {NAME}")
else:
    me = obj.data if obj.type == "MESH" else None
    v = len(me.vertices) if me else 0
    p = len(me.polygons) if me else 0
    print(f"INSPECT {NAME}: type={obj.type} dims={tuple(round(d, 3) for d in obj.dimensions)} "
          f"verts={v} polys={p} loc={tuple(round(c, 3) for c in obj.location)}")
