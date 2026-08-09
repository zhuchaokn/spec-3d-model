"""op: export — 导出各可打印件为 STL,并存一份 .blend 到 output/。

一个"可打印件"可能由**多个重叠的独立对象**组成(如筐半 + 它的卡合件),它们一起
导出到同一个 STL,切片器会自动合并。

ctx.params:
  pieces      : { 文件名: [对象名, ...] }  每个键=一个 STL,值=组成它的对象们
  out_dir     : 输出目录(绝对路径)
  blend_name  : .blend 文件名(可选)
在最后(spread 之后)跑。output/ 已 gitignore。
"""
import os
import bpy
import s3d


def run(ctx):
    pieces = ctx.params["pieces"]
    out_dir = ctx.params["out_dir"]
    os.makedirs(out_dir, exist_ok=True)
    done = []
    for fname, names in pieces.items():
        objs = [bpy.data.objects.get(n) for n in names]
        objs = [o for o in objs if o is not None]
        if not objs:
            print(f"  [export] skip 空: {fname}")
            continue
        fp = os.path.join(out_dir, f"{fname}.stl")
        s3d.export_stl(objs, fp)
        done.append(f"{fname}.stl({len(objs)}件)")
    blend = ctx.params.get("blend_name")
    if blend:
        s3d.save_blend(os.path.join(out_dir, blend))
        done.append(blend)
    print(f"  [export] → {out_dir}: {done}")
