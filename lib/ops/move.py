"""op: move — 平移一个已存在对象(展示/分件:把两半拉开)。

ctx.params: target_name(要移动的对象),delta=[dx,dy,dz] cm。
不新增对象,只改 location。ctx.target 里对象也可,但这里用 params 显式指定更清晰。
"""
import bpy
import s3d


def run(ctx):
    name = ctx.params["target_name"]
    o = bpy.data.objects.get(name)
    if o is None:
        raise ValueError(f"move {ctx.name}: {name} 不存在")
    dx, dy, dz = ctx.params["delta"]
    o.location = (o.location.x + dx * s3d.CM,
                  o.location.y + dy * s3d.CM,
                  o.location.z + dz * s3d.CM)
    print(f"  [move] {name} += ({dx},{dy},{dz})cm")
