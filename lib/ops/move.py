"""op: move — 平移一批已存在对象(展示/分件:把一组零件整体挪开)。

ctx.params: names=[对象名...](或单个 target_name),delta=[dx,dy,dz] cm。
不新增对象,只改 location。因为零件常是"独立摆在重叠位置"的一组(如筐半+其卡合件),
移动时要整组一起移,故支持多名。
"""
import bpy
import s3d


def run(ctx):
    names = ctx.params.get("names") or [ctx.params["target_name"]]
    dx, dy, dz = ctx.params["delta"]
    for name in names:
        o = bpy.data.objects.get(name)
        if o is None:
            raise ValueError(f"move {ctx.name}: {name} 不存在")
        o.location = (o.location.x + dx * s3d.CM,
                      o.location.y + dy * s3d.CM,
                      o.location.z + dz * s3d.CM)
    print(f"  [move] {names} += ({dx},{dy},{dz})cm")
