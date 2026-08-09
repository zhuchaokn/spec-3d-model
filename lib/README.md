# lib/ — 通用层:引擎 + 原子 + 操作

spec-3d-model 的通用层,跨项目共享:
- **`engine.py`** — 构建引擎(纯调度器)。
- **`s3d.py`** — 无业务 bpy 原子 + 坐标助手 + 读场景。业务几何(六边形/凹沿…)不进这里,进 `ops/`。
- **`ops/*.py`** — 操作原子,签名 `run(ctx)`:box/subtract/frustum/hex_array/scallop/cclip/capsule_cut/mirror/move。
- **`ENGINE.md`** — ★ 引擎权威方案,**做新项目先读它**(字段语义、op 契约、表达式、坐标、工程原则、建项目步骤)。

## 用法

项目 `run_model.py` 把 `lib/` 加进 `sys.path`,`reload(s3d, engine)` 后
`engine.run_model(".../model.json")`(命名空间每次全新,故需 reload,见 CLAUDE.md bootstrap)。

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
| `add_frustum(name, dia_bot_cm, dia_top_cm, h_cm, loc_cm, seg)` | 建竖直圆台/锥台(轴=Z,底顶异径) | dia_top=0锥/=底柱 | obj |
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
| `bbox(name)` | 世界包围盒 dict(min/max/center/size,cm) | — | dict/None |
| `scene_dump()` | 读全场景 mesh → list[dict](名/尺寸/质心/面/水密),核对用 | — | list |
| `heal(name, dist_cm)` | 合并重复顶点+重算法线,修布尔残边 | dist_cm=0.001 | 非流形数 |
| `manifold_report(name)` | 边分类 dict(boundary漏洞/nonmanifold自交/total) | — | dict/None |

## ops/ 操作索引(签名 `run(ctx)`,详见 ENGINE.md §4)

| op | 作用 | 关键 params |
|---|---|---|
| `box` | 建具名长方体(实体) | size |
| `subtract` | 临时盒切割器从 target 布尔减 | size |
| `frustum` | 圆台,有 target 则 union 进去 | d_bot,d_top,h |
| `capsule_cut` | 胶囊镂空从 target 减(把手) | w,h,depth,axis |
| `scallop` | 长墙 `\___/` 凹沿梯形切割 | L,W,H,dip,corner,flat,over |
| `hex_array` | 四壁+底铺六边形合并一次布尔减 | hex_w,gap,wall,margin_*,seam_*,handle,scallop,full_L |
| `cclip` | 建 C 夹(墩−孔−缝)union 进 target | od,id,slot_w,h,open |
| `mirror` | 跨 X=0 镜像 source 成新对象 | source |
| `move` | 平移已存在对象(拉开两半) | target_name,delta |
| `heal` | 修网格(合并重复顶点)+ 报告 边界边/非流形 | target_name,dist |

## 新增原子/op 的判据

- 跨项目、无业务的几何能力(布尔、建圆柱、坐标换算)→ `s3d.py`。
- 一种"怎么建"的操作(可复用)→ `ops/<name>.py`,签名 `run(ctx)`。
- 编码某产品设计意图的具体尺寸/坐标 → 项目的 `model.json`,不进 lib。
- 新增后同步本表与 `ENGINE.md`。
