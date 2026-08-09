"""run_model.py — 在 Blender 里跑注册表构建 basket。

用法:execute_blender_code(file_path=".../projects/basket/run_model.py")
改 MODEL 指向要跑的注册表 JSON。命名空间每次全新 + sys.modules 缓存,故 reload。
"""
import sys, importlib, os

LIB = "/Users/zhuchao14/blender/lib"
PROJ = "/Users/zhuchao14/blender/projects/basket"
if LIB not in sys.path:
    sys.path.insert(0, LIB)

import s3d, engine
importlib.reload(s3d); importlib.reload(engine)

MODEL = os.path.join(PROJ, "model.json")   # ← 切换注册表


def main():
    s3d.set_cm_units()
    built = engine.run_model(MODEL, lib_dir=LIB)
    # 数据验证:dump 场景核对
    dump = s3d.scene_dump()
    print(f"OK run_model built={built}")
    for d in dump:
        print(f"  scene: {d['name']} dims={d['dims_cm']} verts={d['verts']} watertight={d.get('watertight')}")


main()
