"""op: export — 把指定对象各导出为 STL,并存一份 .blend 到项目 output/。

ctx.params:
  parts       : 要各自导出 STL 的对象名列表(每个=一个可打印件)
  out_dir     : 输出目录(绝对路径)
  blend_name  : .blend 文件名(可选,不给则不存 blend)
在 spread 之后跑(导出的是最终摆放)。output/ 已 gitignore。
"""
import os
import bpy
import s3d


def run(ctx):
    parts = ctx.params["parts"]
    out_dir = ctx.params["out_dir"]
    os.makedirs(out_dir, exist_ok=True)
    done = []
    for name in parts:
        obj = bpy.data.objects.get(name)
        if obj is None:
            print(f"  [export] skip 缺失: {name}")
            continue
        fp = os.path.join(out_dir, f"{name}.stl")
        s3d.export_stl(obj, fp)
        done.append(os.path.basename(fp))
    blend = ctx.params.get("blend_name")
    if blend:
        bp = s3d.save_blend(os.path.join(out_dir, blend))
        done.append(os.path.basename(bp))
    print(f"  [export] → {out_dir}: {done}")
