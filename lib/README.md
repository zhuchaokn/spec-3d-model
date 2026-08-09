# lib/ — 第0层:通用原子能力

spec-3d-model 的最底层。只放**与业务无关、任何 3D 建模都会用到**的 bpy 原子。
筐子的六边形/凹沿/把手等**业务几何不进这里**,它们属于各 project 的 `components/`。

## 用法

project 的 `build.py` 头部把 `lib/` 加进 `sys.path` 后 `from s3d import *`
(`execute_blender_code` 每次命名空间全新,故需 `importlib.reload`,见 CLAUDE.md 的 bootstrap)。

单位约定:**对外参数一律 cm**;`CM = 0.01` 换算到 Blender 内部的米。

## s3d.py 原子索引

| 函数 | 用途 | 关键参数 | 返回 |
|---|---|---|---|
| `vadd/vsub(a,b)` `vscale(a,k)` | 3元组向量加/减/数乘(cm) | — | (x,y,z) |
| `rel_to_abs(rel, ref_center)` | 相对坐标→绝对(相对+参照质心),可链式叠加 | — | (x,y,z) |
| `box_corner(center, size, sx,sy,sz)` | 长方体角/面中心绝对坐标;s∈{-1,0,1}选轴负/中/正 | — | (x,y,z) |
| `face_center(center, size, axis, sign)` | 长方体某面中心绝对坐标 | axis∈x/y/z, sign±1 | (x,y,z) |
| `wall_center(box_center, size, axis, sign)` | 把某面当"虚拟墙"质心(框无独立墙object时用) | — | (x,y,z) |
| `sel(obj, only=True)` | 选中并设为活动对象 | only=先取消其他选择 | obj |
| `add_box(name, size_cm, loc_cm)` | 建具名长方体(scale 已 apply) | size_cm=(x,y,z), loc_cm=中心 | obj |
| `add_cylinder(name, dia_cm, h_cm, loc_cm, seg)` | 建竖直圆柱(轴=Z) | dia/h cm, seg 分段 | obj |
| `prism(name, pts_uv, orient, face_pos_cm, cu_cm, cv_cm, depth_cm, v_center_cm)` | 任意 2D 轮廓沿法向拉伸的流形棱柱(通用切割器) | orient∈{wall_y,wall_x,bottom} | obj |
| `capsule(name, length_cm, height_cm, depth_cm, loc_cm, axis, seg)` | 胶囊柱(中间矩形+两端半圆) | axis=拉伸法向 | obj |
| `bool_diff(target, cutter, apply, remove_cutter)` | target − cutter(EXACT) | 默认 apply+删 cutter | target |
| `bool_union(target, other, apply, remove_other)` | target ∪ other(EXACT) | 默认 apply+删 other | target |
| `bool_diff_many(target, cutters)` | 多 cutter 先 join 再一次布尔(快) | — | target |
| `join_objs(target, others)` | 合并 others 进 target(保留 target 名) | — | target |
| `copy_object(src, new_name)` | 深拷贝(独立 mesh 数据) | — | dup |
| `clean_by_names(names, prefixes)` | 幂等清理:按名/前缀删对象 | — | 删除数 |
| `set_cm_units()` | 场景显示单位设为 cm | — | — |
| `export_stl(obj, filepath)` | 导出 STL(4.x/3.x 版本兼容) | — | filepath |
| `save_blend(filepath)` | 保存 .blend | — | filepath |
| `inspect(name)` | 网格统计 dict(dims_cm/verts/polys/loc_cm) | — | dict/None |
| `is_watertight(name)` | 简易水密检查(每边恰好 2 面) | — | bool/None |

## 新增原子的判据

只有当某能力**跨项目、与具体产品无关**时才加进 `s3d.py`(如"两 object 做布尔"、"建圆柱")。
若它编码了某个产品的设计意图(如"六边形蜂巢孔阵列"),放到该 project 的 component 里。
新增后同步本表。
