"""list_objects.py — 列出场景中所有 mesh 对象的名称、尺寸、位置。

幂等：只读，重跑安全，无副作用。
用途：执行创建/修改脚本后验证场景现状。
输出：print "SCENE_OBJECTS: [(name, dims, loc), ...]"。
"""
import bpy

objs = [
    (o.name, tuple(round(d, 3) for d in o.dimensions), tuple(round(c, 3) for c in o.location))
    for o in bpy.data.objects
    if o.type == "MESH"
]
print("SCENE_OBJECTS:", objs)
