"""export.py — 导出各打印部件 STL + 保存 .blend 到 output/。

用法:execute_blender_code(file_path=此文件)。
"""
import os, sys, importlib
LIB = "/Users/zhuchao14/blender/lib"
PROJ = "/Users/zhuchao14/blender/projects/<name>"   # ← 改成本项目路径
for _p in (LIB, PROJ):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import s3d
importlib.reload(s3d)
from s3d import export_stl, save_blend    # noqa: E402
import bpy                                # noqa: E402

# 要导出为独立 STL 的部件名(每个是一个可打印件)
PARTS = [
    # "BasketL", "BasketR",
]


def main():
    out = os.path.join(PROJ, "output")
    os.makedirs(out, exist_ok=True)
    done = []
    for name in PARTS:
        obj = bpy.data.objects.get(name)
        if obj is None:
            print(f"  skip missing: {name}"); continue
        fp = os.path.join(out, f"{name}.stl")
        export_stl(obj, fp)
        done.append(os.path.basename(fp))
    blend = save_blend(os.path.join(out, "<name>.blend"))
    print(f"OK exported {done} + {os.path.basename(blend)}")


main()
