"""run_model.py — 在 Blender 里跑注册表构建 basket。

用法:execute_blender_code(file_path=".../projects/basket/run_model.py")
命名空间每次全新 + sys.modules 缓存,故 reload。
自定位:server 注入 __file__,PROJ/LIB 从它反推;回落 SPEC3D_ROOT 环境变量。
"""
import sys, importlib, os


def _locate():
    if "__file__" in globals():
        proj = os.path.dirname(os.path.abspath(__file__))
        root = os.path.dirname(os.path.dirname(proj))
        return proj, os.path.join(root, "lib")
    root = os.environ.get("SPEC3D_ROOT")
    if not root:
        raise RuntimeError("无 __file__ 且未设 SPEC3D_ROOT,无法定位项目路径")
    return os.path.join(root, "projects", "basket"), os.path.join(root, "lib")


PROJ, LIB = _locate()
if LIB not in sys.path:
    sys.path.insert(0, LIB)

import s3d, engine
importlib.reload(s3d); importlib.reload(engine)

MODEL = os.path.join(PROJ, "model.json")   # ← 切换注册表


def main():
    # 清场:每次全量构建从空场景开始(避免上次残留/调试污染)
    import bpy
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    s3d.set_cm_units()
    built = engine.run_model(MODEL, lib_dir=LIB)
    # 数据验证:dump 场景核对
    dump = s3d.scene_dump()
    print(f"OK run_model built={built}")
    for d in dump:
        print(f"  scene: {d['name']} dims={d['dims_cm']} verts={d['verts']} watertight={d.get('watertight')}")


main()
