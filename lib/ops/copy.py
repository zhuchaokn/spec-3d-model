"""op: copy — 复制一个已存在对象为新具名对象,放到 ctx.center。

ctx.params: source(要复制的对象名)。ctx.center=新对象质心(绝对)。
常用于:复制一个已建好的零件当**一次性切割器**(配合 cut op 从别处减掉),
不必重算它的形状/尺寸。深拷贝,独立 mesh。
"""
import s3d
import bpy


def run(ctx):
    src = bpy.data.objects.get(ctx.params["source"])
    if src is None:
        raise ValueError(f"copy {ctx.name}: source {ctx.params['source']} 不存在")
    s3d.clean_by_names(names=(ctx.name,))
    dup = s3d.copy_object(src, ctx.name)
    dup.location = tuple(v * s3d.CM for v in ctx.center)
    print(f"  [copy] {ctx.name} = copy({src.name}) @ {tuple(round(c,3) for c in ctx.center)}")
