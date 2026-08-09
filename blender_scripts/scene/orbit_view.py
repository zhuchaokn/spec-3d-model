"""orbit_view.py — 设置 3D 视口到方位角/俯仰角/距离的视角，便于截图观察模型。

是否幂等：是（只改当前视口视角，不增删对象）。
方位约定：AZIMUTH 0°=正前(+Y 朝原点看), 90°=右侧(+X), 180°=后, 270°=左；
ELEVATION 0°=平视, 正=俯视, 负=仰视。DISTANCE/TARGET 均用 cm。
可调参数见下方常量，改完用 execute_blender_code(file_path=__file__) 跑。
输出：最后一行 print 结果。
"""
import bpy
from mathutils import Vector, Matrix
from math import radians, sin, cos

# ---- params (edit me) ----
AZIMUTH = 210.0         # 度：水平方位（斜后看两半内侧+中缝卡合）
ELEVATION = 28.0        # 度：俯仰
DISTANCE = 58.0         # cm：相机到目标距离
TARGET = (0.0, 0.0, 9.0)    # cm：观察焦点(整体)
PERSP = True            # True=透视, False=正交
ZOOM = 0                # 正交缩放(越小越近)；<=0 用默认
# --------------------------

M = 1.0 / 100.0


def _set_view():
    target = Vector((TARGET[0] * M, TARGET[1] * M, TARGET[2] * M))
    dist = DISTANCE * M
    az = radians(AZIMUTH)
    el = radians(ELEVATION)
    pos = target + Vector((sin(az) * cos(el), cos(az) * cos(el), sin(el))) * dist
    up = Vector((0, 0, 1))
    z = (pos - target).normalized()
    x = up.cross(z)
    if x.length < 1e-6:
        x = Vector((1, 0, 0))
    x.normalize()
    y = z.cross(x).normalized()
    view = Matrix((x, y, z)).to_4x4()
    view[0][3] = -x.dot(pos)
    view[1][3] = -y.dot(pos)
    view[2][3] = -z.dot(pos)
    applied = False
    for area in bpy.context.screen.areas:
        if area.type != 'VIEW_3D':
            continue
        for sp in area.spaces:
            if sp.type != 'VIEW_3D':
                continue
            rv3d = sp.region_3d
            if rv3d is None:
                continue
            rv3d.view_perspective = 'PERSP' if PERSP else 'ORTHO'
            rv3d.view_matrix = view
            if not PERSP and ZOOM and ZOOM > 0:
                rv3d.view_distance = ZOOM  # 正交下由 view_distance 控制可见范围(米)
            rv3d.update()
            applied = True
    return applied


applied = _set_view()
print(f"OK view set az={AZIMUTH} el={ELEVATION} dist={DISTANCE}cm target={TARGET} "
      f"persp={PERSP} applied={applied}")
