"""build.py — 部件 <part>。

幂等:开头按名/前缀清理旧对象。产出具名对象。末尾 print 一行结果。
独立可跑:execute_blender_code(file_path=此文件)。依赖前序对象须已在场景中。
"""
import sys, importlib

# ---- bootstrap:命名空间每次全新 + sys.modules 缓存,故加路径并 reload ----
LIB = "/Users/zhuchao14/blender/lib"
PROJ = "/Users/zhuchao14/blender/projects/<name>"   # ← 改成本项目路径
for _p in (LIB, PROJ):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import s3d, params
importlib.reload(s3d); importlib.reload(params)
from s3d import *          # noqa: F401,F403
from params import *       # noqa: F401,F403
# ---------------------------------------------------------------

import bpy  # noqa: E402


def main():
    clean_by_names(names=("<Obj>",), prefixes=("Cutter",))
    set_cm_units()

    # ... 用 s3d 原子 + params 常量构建本部件 ...
    # obj = add_box("<Obj>", (LENGTH, WIDTH, HEIGHT), (0, 0, HEIGHT / 2))

    info = inspect("<Obj>")
    print(f"OK <part>: {info}")


main()
