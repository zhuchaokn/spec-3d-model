"""run_model.py — 在 Blender 里跑本项目的 model.json 构建。

用法:execute_blender_code(file_path=".../projects/clip_tester/run_model.py")
命名空间每次全新 + sys.modules 缓存,故 reload;每次全量构建先清场。
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
    return os.path.join(root, "projects", "clip_tester"), os.path.join(root, "lib")


PROJ, LIB = _locate()
if LIB not in sys.path:
    sys.path.insert(0, LIB)

import s3d, engine
importlib.reload(s3d); importlib.reload(engine)

import bpy


def main():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)   # 清场
    s3d.set_cm_units()
    model = os.path.join(PROJ, "model.json")
    built = engine.run_model(model, lib_dir=LIB)
    print(f"OK built={built}")
    for d in s3d.scene_dump():
        r = s3d.manifold_report(d["name"])
        print(f"  {d['name']} dims={d['dims_cm']} 漏洞={r['boundary']} 非流形={r['nonmanifold']}")


main()
