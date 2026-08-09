"""s3d.py — 通用几何原子(与业务无关,跨项目共享)。

只放"任何 3D 建模都会用到"的原子:建盒/柱/圆台、任意流形棱柱、胶囊、布尔、
join、按名清理、单位设置、坐标换算、导出 STL、读场景、网格诊断。
**不含任何具体产品逻辑**——编码某产品设计意图的几何属于 op(见 lib/ops 或项目 ops)。

单位约定:所有对外参数用 **cm**;Blender 内部单位是米,故 CM=0.01 换算。
op 脚本内 `import s3d` 调用即可(引擎已把 lib 加入 sys.path)。索引见 lib/README.md。
"""
import bpy
import bmesh
from math import pi, cos, sin

CM = 1.0 / 100.0  # cm → Blender 米


# ---- 坐标计算(绝对/相对换算;详见 CLAUDE.md「坐标系统」) ----
# 约定:坐标是 3 元组 (x,y,z),单位 cm;物体定位指其**质心**。

def vadd(a, b):
    """向量相加(逐分量)。"""
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def vsub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def vscale(a, k):
    return (a[0] * k, a[1] * k, a[2] * k)


def rel_to_abs(rel, ref_center):
    """相对坐标 → 绝对坐标:绝对 = 相对 + 参照物质心。可链式叠加多级参照。"""
    return vadd(rel, ref_center)


def box_corner(center, size, sx, sy, sz):
    """长方体某角/面中心的绝对坐标。center=质心,size=(L,W,H);
    sx,sy,sz ∈ {-1,0,+1} 选该轴的 负面/中心/正面。
    如 face_+X 中心=box_corner(c,s,1,0,0);顶面=(...,0,0,1);角=(±1,±1,±1)。"""
    return (center[0] + sx * size[0] / 2,
            center[1] + sy * size[1] / 2,
            center[2] + sz * size[2] / 2)


def face_center(center, size, axis, sign):
    """长方体某个面的中心绝对坐标。axis∈{'x','y','z'},sign∈{+1,-1}。"""
    s = {'x': (sign, 0, 0), 'y': (0, sign, 0), 'z': (0, 0, sign)}[axis]
    return box_corner(center, size, *s)


def wall_center(box_center, size, axis, sign):
    """把长方体的某面当作一堵'虚拟墙'的质心(= 该面中心)返回其绝对坐标。
    用于框体没有独立墙 object 时,先定位墙、再在墙的相对系里放卡合件。
    如取盒子的 +Y 面作参照:wall_center(box_center, (L,W,H), 'y', +1)。"""
    return face_center(box_center, size, axis, sign)


# ---- 选择 / 上下文 ----

def sel(obj, only=True):
    """把 obj 设为选中+活动对象。only=True 先取消其他选择。"""
    if only:
        bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    return obj


# ---- 图元 ----

def add_box(name, size_cm, loc_cm=(0, 0, 0)):
    """建具名长方体。size_cm=(x,y,z) 外尺寸 cm,loc_cm 中心。scale 已 apply。"""
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=tuple(v * CM for v in loc_cm))
    o = bpy.context.active_object
    o.name = name
    o.scale = tuple(v * CM for v in size_cm)
    sel(o)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return o


def add_cylinder(name, dia_cm, h_cm, loc_cm=(0, 0, 0), seg=64):
    """建竖直圆柱(轴=Z)。dia_cm 直径,h_cm 高,loc_cm 中心,seg 分段。"""
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=seg, radius=dia_cm / 2 * CM, depth=h_cm * CM,
        location=tuple(v * CM for v in loc_cm))
    o = bpy.context.active_object
    o.name = name
    return o


def add_frustum(name, dia_bot_cm, dia_top_cm, h_cm, loc_cm=(0, 0, 0), seg=64):
    """建竖直圆台/锥台(轴=Z):底径 dia_bot、顶径 dia_top、高 h,质心在 loc。

    dia_top=0 即圆锥;dia_top=dia_bot 即圆柱。"""
    bpy.ops.mesh.primitive_cone_add(
        vertices=seg, radius1=dia_bot_cm / 2 * CM, radius2=dia_top_cm / 2 * CM,
        depth=h_cm * CM, location=tuple(v * CM for v in loc_cm))
    o = bpy.context.active_object
    o.name = name
    return o


def prism(name, pts_uv, orient, face_pos_cm, cu_cm, cv_cm, depth_cm, v_center_cm=0.0):
    """通用流形棱柱:2D 轮廓 pts_uv(cm) 沿法向拉伸 depth_cm。

    常用作布尔切割器(在墙面/底面上切出任意轮廓的洞)。orient 决定轮廓平面朝向:
      'wall_y' 法向=Y、轮廓 u=X v=Z(用于前/后墙)
      'wall_x' 法向=X、轮廓 u=Y v=Z(用于左/右墙)
      'bottom' 法向=Z、轮廓 u=X v=Y(用于底板)
    face_pos_cm=法向位置(如墙面 Y),cu/cv=沿/上方向中心,v_center=轮廓 v 居中偏移。
    产出的对象是流形闭合棱柱,法线已更新,适合 EXACT 布尔。
    """
    def w(u, v, t):
        au, av = u, v - v_center_cm
        if orient == 'wall_y':
            return ((cu_cm + au) * CM, (face_pos_cm + t) * CM, (cv_cm + av) * CM)
        if orient == 'wall_x':
            return ((face_pos_cm + t) * CM, (cu_cm + au) * CM, (cv_cm + av) * CM)
        return ((cu_cm + au) * CM, (cv_cm + av) * CM, (face_pos_cm + t) * CM)

    return _extrude_profile(name, pts_uv, w, depth_cm)


def capsule(name, length_cm, height_cm, depth_cm, loc_cm=(0, 0, 0), axis='x', seg=24):
    """建胶囊柱(中间矩形+两端半圆),沿 depth 方向拉伸。常用作圆角长孔的切割器。

    length_cm=胶囊总长(含两端半圆),height_cm=胶囊高(=2*半径),
    depth_cm=拉伸厚度,axis=拉伸法向('x'/'y'/'z')。轮廓在垂直于 axis 的平面。
    """
    r = height_cm / 2
    sr = length_cm / 2 - r
    perim = []
    for i in range(seg + 1):
        a = -pi / 2 + pi * i / seg
        perim.append((sr + r * cos(a), r * sin(a)))
    for i in range(1, seg + 1):
        a = pi / 2 + pi * i / seg
        perim.append((-sr + r * cos(a), r * sin(a)))

    cx, cy, cz = (v * CM for v in loc_cm)

    def w(p, q, t):
        # (p,q) 轮廓两轴, t 沿法向 axis;p/q/t 均 cm,此处统一 *CM
        if axis == 'x':
            return (cx + t * CM, cy + p * CM, cz + q * CM)
        if axis == 'y':
            return (cx + p * CM, cy + t * CM, cz + q * CM)
        return (cx + p * CM, cy + q * CM, cz + t * CM)

    return _extrude_profile(name, perim, w, depth_cm)


def _extrude_profile(name, pts, w, depth_cm):
    """内部:把 2D 轮廓 pts 用坐标函数 w(u,v,t) 拉伸成闭合棱柱。

    w(u,v,t) 接收轮廓两轴值+法向偏移 t,全部 cm(w 内部再统一 *CM 换算);
    t=±depth_cm/2 为前后面。"""
    n = len(pts)
    bm = bmesh.new()
    back = [bm.verts.new(w(u, v, -depth_cm / 2)) for (u, v) in pts]
    front = [bm.verts.new(w(u, v, depth_cm / 2)) for (u, v) in pts]
    bm.faces.new(back)
    bm.faces.new(list(reversed(front)))
    for i in range(n):
        bm.faces.new((back[i], back[(i + 1) % n], front[(i + 1) % n], front[i]))
    bm.normal_update()
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(obj)
    return obj


# ---- 布尔 / 合并 ----

def bool_diff(target, cutter, apply=True, remove_cutter=True):
    """target 减去 cutter(EXACT 求解器)。默认 apply 并删除 cutter。"""
    sel(target)
    mod = target.modifiers.new("Bool", 'BOOLEAN')
    mod.object = cutter
    mod.operation = 'DIFFERENCE'
    mod.solver = 'EXACT'
    if apply:
        bpy.ops.object.modifier_apply(modifier=mod.name)
        if remove_cutter and cutter.name in bpy.data.objects:
            bpy.data.objects.remove(cutter, do_unlink=True)
    return target


def bool_union(target, other, apply=True, remove_other=True):
    """target 并 other(EXACT)。默认 apply 并删除 other。"""
    sel(target)
    mod = target.modifiers.new("Bool", 'BOOLEAN')
    mod.object = other
    mod.operation = 'UNION'
    mod.solver = 'EXACT'
    if apply:
        bpy.ops.object.modifier_apply(modifier=mod.name)
        if remove_other and other.name in bpy.data.objects:
            bpy.data.objects.remove(other, do_unlink=True)
    return target


def heal(name, dist_cm=0.001):
    """修网格:合并极近重复顶点 + 重算法线朝外。修布尔/union 留下的非流形残边。

    dist_cm 默认 0.001cm(=0.01mm),只并真正重合的点,不动正常几何。返回修后非流形边数。"""
    obj = bpy.data.objects.get(name)
    if obj is None or obj.type != "MESH":
        return None
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=dist_cm * CM)
    bm.normal_update()
    nm = sum(1 for e in bm.edges if len(e.link_faces) > 2)
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    return nm


def join_objs(target, others):
    """把 others 合并进 target(join,保留 target 名)。"""
    bpy.ops.object.select_all(action='DESELECT')
    for o in others:
        o.select_set(True)
    target.select_set(True)
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.join()
    return target


def bool_diff_many(target, cutters):
    """把多个 cutter 先 join 再一次布尔(比逐个布尔快很多)。清理临时对象。"""
    if not cutters:
        return target
    bpy.ops.object.select_all(action='DESELECT')
    for c in cutters:
        c.select_set(True)
    bpy.context.view_layer.objects.active = cutters[0]
    bpy.ops.object.join()
    joined = bpy.context.active_object
    joined.name = "_CutterMerged"
    bool_diff(target, joined)
    return target


# ---- 清理 / 单位 ----

def clean_by_names(names=(), prefixes=()):
    """幂等清理:删名字在 names 或以 prefixes 任一前缀开头的对象。

    op 内建对象前调用以保证重跑不产生重复对象(引擎入口也会先清场)。返回删除数。"""
    removed = 0
    for obj in list(bpy.data.objects):
        if obj.name in names or any(obj.name.startswith(p) for p in prefixes):
            bpy.data.objects.remove(obj, do_unlink=True)
            removed += 1
    return removed


def set_cm_units():
    """把场景显示单位设为厘米(仅显示;内部仍是米)。"""
    us = bpy.context.scene.unit_settings
    us.system = 'METRIC'
    us.length_unit = 'CENTIMETERS'


def copy_object(src, new_name):
    """深拷贝对象(含独立 mesh 数据),链接到当前 collection,改名返回。"""
    dup = src.copy()
    dup.data = src.data.copy()
    bpy.context.collection.objects.link(dup)
    dup.name = new_name
    return dup


# ---- 导出 / 验证 ----

def export_stl(objs, filepath):
    """导出一个或一组对象为一个 STL(重叠的独立零件一起导出=同一可打印件)。
    objs 可为单个对象或对象列表。兼容 Blender 4.x(新算子)与 3.x(旧 export_mesh)。"""
    if not isinstance(objs, (list, tuple)):
        objs = [objs]
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    if bpy.app.version >= (4, 2):
        bpy.ops.wm.stl_export(filepath=filepath, export_selected_objects=True)
    else:
        bpy.ops.export_mesh.stl(filepath=filepath, use_selection=True)
    return filepath


def save_blend(filepath):
    """保存当前 .blend 到 filepath。"""
    bpy.ops.wm.save_as_mainfile(filepath=filepath)
    return filepath


def inspect(name):
    """返回对象网格统计 dict(尺寸cm/顶点/面/位置/是否流形-简易)。找不到返回 None。"""
    obj = bpy.data.objects.get(name)
    if obj is None:
        return None
    me = obj.data if obj.type == "MESH" else None
    dims_cm = tuple(round(d / CM, 3) for d in obj.dimensions)
    loc_cm = tuple(round(c / CM, 3) for c in obj.location)
    return {
        "name": name, "type": obj.type, "dims_cm": dims_cm, "loc_cm": loc_cm,
        "verts": len(me.vertices) if me else 0,
        "polys": len(me.polygons) if me else 0,
    }


def bbox(name):
    """返回对象的世界包围盒(cm):dict(min=(x,y,z), max=(x,y,z), center, size)。找不到 None。"""
    obj = bpy.data.objects.get(name)
    if obj is None:
        return None
    import mathutils  # noqa
    corners = [obj.matrix_world @ mathutils.Vector(c) for c in obj.bound_box]
    xs = [c.x / CM for c in corners]
    ys = [c.y / CM for c in corners]
    zs = [c.z / CM for c in corners]
    mn = (min(xs), min(ys), min(zs))
    mx = (max(xs), max(ys), max(zs))
    return {"min": mn, "max": mx,
            "center": ((mn[0]+mx[0])/2, (mn[1]+mx[1])/2, (mn[2]+mx[2])/2),
            "size": (mx[0]-mn[0], mx[1]-mn[1], mx[2]-mn[2])}


def scene_dump():
    """读取当前场景全部 mesh 对象 → list[dict](名/尺寸cm/质心cm/面数/水密)。

    读真实场景态,供与注册表 resolve 结果比对(即使人手改了 Blender 也能读回核对)。"""
    out = []
    for o in bpy.data.objects:
        if o.type != "MESH":
            continue
        me = o.data
        out.append({
            "name": o.name,
            "dims_cm": tuple(round(d / CM, 3) for d in o.dimensions),
            "loc_cm": tuple(round(c / CM, 3) for c in o.location),
            "verts": len(me.vertices),
            "polys": len(me.polygons),
            "watertight": is_watertight(o.name),
        })
    return out


def manifold_report(name):
    """边拓扑分类:boundary=边界边(真漏洞,应=0)、nonmanifold=>2面的T形交线
    (柱穿墙等自交,切片器可容忍)、total。用于区分"漏洞"与"可打印的自交"。"""
    obj = bpy.data.objects.get(name)
    if obj is None or obj.type != "MESH":
        return None
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    boundary = sum(1 for e in bm.edges if len(e.link_faces) < 2)
    nonmani = sum(1 for e in bm.edges if len(e.link_faces) > 2)
    total = len(bm.edges)
    bm.free()
    return {"boundary": boundary, "nonmanifold": nonmani, "total": total}


def is_watertight(name):
    """简易水密检查:每条边恰好被 2 个面共享(非流形/边界边即为 False)。"""
    obj = bpy.data.objects.get(name)
    if obj is None or obj.type != "MESH":
        return None
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    ok = all(len(e.link_faces) == 2 for e in bm.edges)
    bm.free()
    return ok
