"""verify.py — 数据验证(不截图)。

用几何数据核对成品是否符合预期:部件数、尺寸、面数、水密性。
视觉判断交给人。用法:execute_blender_code(file_path=此文件)。
"""
import sys, importlib
LIB = "/Users/zhuchao14/blender/lib"
PROJ = "/Users/zhuchao14/blender/projects/<name>"   # ← 改成本项目路径
for _p in (LIB, PROJ):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import s3d, params
importlib.reload(s3d); importlib.reload(params)
from s3d import inspect, is_watertight   # noqa: E402

# 期望产出的部件名(填本项目)
EXPECT = [
    # "BasketL", "BasketR",
]


def main():
    ok = True
    for name in EXPECT:
        info = inspect(name)
        if info is None:
            print(f"FAIL missing: {name}"); ok = False; continue
        wt = is_watertight(name)
        print(f"  {name}: dims={info['dims_cm']}cm verts={info['verts']} "
              f"polys={info['polys']} watertight={wt}")
        if wt is False:
            ok = False
    print("OK verify passed" if ok else "FAIL verify")


main()
