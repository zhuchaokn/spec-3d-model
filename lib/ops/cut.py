"""op: cut — 用一个已存在对象当切割器,从 target 布尔减掉,然后删除切割器。

ctx.params: tool(切割器对象名)。ctx.targets: 被减对象(可多)。
与 subtract 的区别:subtract 现场建一个盒当切割器;cut 用**已存在的任意形状对象**
(常是 copy 出来的一次性件)。减完删除该切割器。
"""
import s3d
import bpy


def run(ctx):
    tool = bpy.data.objects.get(ctx.params["tool"])
    if tool is None:
        raise ValueError(f"cut {ctx.name}: tool {ctx.params['tool']} 不存在")
    tnames = []
    for dep in ctx.targets.values():
        tgt = dep["object"]
        if tgt is None:
            raise ValueError(f"cut {ctx.name}: target 不存在")
        s3d.bool_diff(tgt, tool, apply=True, remove_cutter=False)
        tnames.append(tgt.name)
    s3d.clean_by_names(names=(ctx.params["tool"],))   # 用完删切割器
    print(f"  [cut] {tnames} -= {ctx.params['tool']}(已删)")
