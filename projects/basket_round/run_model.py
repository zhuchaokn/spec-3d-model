"""run_model.py — 在 Blender 里跑注册表构建 basket_round(圆润版 basket)。

用法:execute_blender_code(file_path=".../projects/basket_round/run_model.py")
命名空间每次全新 + sys.modules 缓存,故 reload。
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
    return os.path.join(root, "projects", "basket_round"), os.path.join(root, "lib")


PROJ, LIB = _locate()
if LIB not in sys.path:
    sys.path.insert(0, LIB)

import s3d, engine
importlib.reload(s3d); importlib.reload(engine)

MODEL = os.path.join(PROJ, "model.json")


def main():
    import bpy
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    s3d.set_cm_units()
    built = engine.run_model(MODEL, lib_dir=LIB)
    dump = s3d.scene_dump()
    print(f"OK run_model built={built}")
    for d in dump:
        print(f"  scene: {d['name']} dims={d['dims_cm']} verts={d['verts']} watertight={d.get('watertight')}")


main()
