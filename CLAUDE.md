# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# spec-3d-model

用**工程化、分层分治**的方式构建 Blender 3D 打印模型的能力体系。类比 spec-coding:
先写规格、对齐方案,再分部件实现、组合成品。当前范围**仅 3D 建模(用于 3D 打印)**,
暂不涉及动画/材质/渲染。

## 核心思想:构建引擎 + 分层分治

一个模型由**一份 JSON 注册表(唯一真相源)**声明,经**纯调度引擎**建出。分层:

```
lib/                      通用层(跨项目共享)
  engine.py                 构建引擎(纯调度器):求值·resolve坐标·拓扑排序·调 op
  s3d.py                    无业务 bpy 原子:add_box/cylinder/frustum/prism/capsule/bool_*/坐标助手/scene_dump...
  ops/*.py                  操作原子:一个 op=一种"怎么建"逻辑,签名 run(ctx)。box/subtract/frustum/hex_array/scallop/cclip/capsule_cut/mirror/move
  ENGINE.md                 ★ 引擎权威方案(做新项目先读这个)
projects/<name>/          项目层(专属)
  model.json                ★ 唯一真相源:常量 + 对象拓扑(尺寸/parent/相对坐标/调哪个op)
  run_model.py              入口:bootstrap + engine.run_model(model.json)
  spec/requirement.md       需求
  spec/preview.html         手写等比例三视图(方案闸门)
  output/                   .blend / .stl(gitignore)
  screenshots/              视觉验证截图(入库,不随意丢)
```

**引擎不含业务,业务全在 op + JSON 数据。原子不含业务,业务不写进 lib。**
`params.py` 已废除——尺寸是对象的属性,归 `model.json` 的常量与节点。
引擎的字段语义、op 契约、表达式、坐标、工程原则 → 见 **`lib/ENGINE.md`**(权威)。

## 执行模型(必读,决定了架构)

`execute_blender_code(file_path=...)` 把文件内容发给 Blender addon,addon `exec` 后返回 stdout。两个事实:

1. **Python 命名空间每次全新** —— 没有 `__file__`,上次的变量/import 都不在。
2. **Blender 场景 `bpy.data` 持续存在** —— 上次建的对象还在;`sys.modules` 也持续缓存。

推论(硬约束):
- **对象间只经"场景里的具名对象"交接**,不能靠 Python 变量传递。故引擎按拓扑序逐节点建**具名**对象,后续节点靠名字(target)取到前序对象。
- **共享库要 reload**:`sys.modules` 缓存,编辑 `engine.py`/`s3d.py`/op 后不 reload 跑的是旧代码。故 `run_model.py` 头部固定 bootstrap:

```python
import sys, importlib, os
LIB = "/Users/zhuchao14/blender/lib"
if LIB not in sys.path: sys.path.insert(0, LIB)
import s3d, engine
importlib.reload(s3d); importlib.reload(engine)   # 让本地编辑生效
# 每次全量构建先清场,再 engine.run_model(".../model.json", lib_dir=LIB)
```

## 坐标系统(全局方法,所有项目通用)

3D 建模的本质是:**理清有哪些物体、各自的坐标、各自的尺寸,然后靠拼接/布尔组合出整个世界。**
设计阶段的主要工作就是把这三件事列清楚。坐标上分两套,配合使用:

### 绝对坐标 vs 相对坐标

- **绝对坐标**:世界原点为基准。Blender 里实际下刀用的就是绝对坐标,且 `add_box`/`add_cylinder`
  等**定位的是物体质心**。给定质心 + 尺寸,每个角/边/面的坐标都能直接算(如质心 `(cx,cy,cz)`、
  尺寸 `(L,W,H)` → 右面 x=`cx+L/2`、顶面 z=`cz+H/2`)。
- **相对坐标**:以**另一个物体的质心为原点**表达位置。算"A 相对 B 在哪"时极简
  (如 C夹/Pin 相对各自那半筐墙的位置)。
- **换算**:`绝对 = 相对 + 参照物的绝对坐标`。先在相对系里把机构想清楚(好算),
  下刀前再 `+参照物质心` 转成绝对(好画)。这是坐标工作的核心套路。

### 虚拟物体(没有独立 object 的参照系)

有时参照系不是一个真实 object(如一个整体盒子 object,它的某一面"墙"并不是单独物体)。
这时**先算出虚拟参照物相对宿主的坐标**,再逐级换算:

- 例:盒子质心已知,尺寸 `(L,W,H)`。其 +Y 面"墙"相对盒子质心 = `(0, +W/2, 0)`
  → 该墙绝对质心 = `盒子质心 + (0, W/2, 0)`。
- 再把墙上要装的零件表达为"相对该墙质心"的坐标 → 零件绝对 = `墙绝对 + 零件相对`。

一步步 `相对 + 参照绝对` 叠加,虚拟参照系照样能精确定位。在 `model.json` 里这条链就是
`op:null` 的虚拟节点 + 子节点的 `parent`/`offset`,引擎 resolve 出绝对坐标,即建模/布尔的依据。

`lib/s3d.py` 提供坐标助手(`box_corner`/`face_center`/`rel_to_abs` 等)把这套换算固化下来。

## 原则

1. **引擎/原子无业务,业务在 op+JSON**:`engine.py` 只调度;`s3d.py` 是无业务原子;每个 op 编码一种建法;`model.json` 承载该项目的对象/尺寸/坐标/关系。禁止把业务尺寸写进 lib。
2. **场景即接口**:对象间只经**具名对象**交接(命名空间每次全新)。引擎按拓扑序建具名对象,后续节点靠名字(target)取前序对象。
3. **单一尺寸源**:所有尺寸/公差/关系集中在 `model.json`(常量 + 节点)。preview.html 镜像它,改数值只改一处。禁止在 op/脚本里硬编码项目尺寸。
4. **数据验证优先,截图仅在必要时且存档**:默认用 `scene_dump`/`inspect`/`is_watertight`/`bbox` 核对(尺寸/部件/水密)。**只有视觉缺陷(镂空缺失/对称/形态)才截图**,一旦获取存进 `screenshots/` 并说明,不丢弃。
5. **先设计后实施,HTML 是权威规格**:动手建 3D 前,**手写**正交三视图 HTML(正/左/俯 + 等比例 + 尺寸)与需求文档。改 HTML 远比改 3D 便宜——方案闸门。人确认后才写 model.json/op。HTML **直接手写**,不写脚本生成它。等比例:统一 px/cm;镂空按真实铺阵画满;卡合接口画出来。
6. **面向打印**:
   - 按**打印体积**拆件(如 Bambu P2S 256³mm),优先沿最长轴切分;对称件用 `mirror`,拆件用 `move` 拉开。
   - **FDM 友好**:避免大面积水平悬桥(六边形 pointy-top 尖顶朝上)、孔轴顺层线;
   - **切缝避开孔**:分割面附近留"禁孔带"保实体,再加**卡合结构**(C夹+pin)连接;
   - **公差**:配合面留间隙(孔 φ5.12 / 柱身 φ5.0 滑配 / 柱底 φ5.12 过盈防脱,切面让位 ~0.15mm);
   - **先打试配件**:正式拆分前先打小的配合测试件定公差。
7. **切割器探出、顺序正确、隔离调试**:切割器必须探出被切面(不共面);同一对象多次切割用 `after` 显式排序(如 hex 先于 scallop);现象怪时把可疑 op 单独跑在干净盒子上 dump 每步核对。详见 `lib/ENGINE.md` §7。
   - **⚠️ 密集/重叠切割器不能一次 join 再布尔**:`bool_diff_many` 把多个 cutter 先 join 成一个网格再一次 EXACT 布尔。若 cutter **彼此重叠**(如镂空孔缩小、间距等比变密后,相邻六边形 cutter 相交),join 出的网格**自相交**,EXACT 布尔结果是垃圾——会把整面墙几乎全减掉,只在每个孔位残留 6 面的侧壁碎片,看起来像"墙消失/透明"。**判据(不必截图)**:`scene_dump` 里该件 `watertight=False` 且尺寸缩水,或连通块数≈孔数、每块恰 6 面 = 中招。**修法**:cutter 之间会重叠时**逐个 `bool_diff`**(单个 cutter 不自相交,只挖自己那块,绝不误伤墙),见 `projects/basket/ops/hex_array.py`。
8. **"部件不见了"先查数据、勿反复截图**:形态异常(墙没了/穿透/缺件)时,先看 `scene_dump` 的 **尺寸 + `watertight`**——满尺寸且水密=实体完整;尺寸缩水或非水密=真丢了几何。别靠转视角/渲染反复找,workbench 下密集薄壁对比低,肉眼判断不可靠且费时。
9. **单位**:建模用 cm(`s3d.CM=0.01`),场景显示设为 cm(`set_cm_units()`);Blender 内部仍是米。

## 工作流(详见 `lib/ENGINE.md` §8)

1. **init** — `projects/<name>/`,拷 `run_model.py`(改 PROJ/MODEL)。
2. **requirement** — 写 `spec/requirement.md`。
3. **设计:HTML** — **手写**等比例 `spec/preview.html` 三视图作为方案规格。**⛔ 停下与人确认,再进入实施。**
4. **model.json** — 列对象/尺寸/parent/相对坐标/op(设计的核心工作)。复用现有 op,缺能力写新 op。
5. **run + verify** — `run_model` 在 Blender 跑;`scene_dump` 数据验证;必要时截图存档。
6. **export** — 导出各打印部件 STL + 保存 .blend 到 `output/`。

## 仓库地图

- `lib/` — 通用层:
  - `engine.py` 引擎;`s3d.py` 原子(见 `lib/README.md`);`ops/` 通用 op(见 `lib/ops/README.md`);
  - **`ENGINE.md` 引擎使用手册**——写 `model.json`/op 前先读它。
- `projects/<name>/` — 各项目(专属)。`basket` 是完整试点范例,新项目可参照它。
- `templates/project/` — 空项目骨架(引擎流程:`model.json` + `run_model.py` + 三视图模板),init 时拷贝。
- `mcp/blender-mcp/` — BlenderMCP server(连通 Blender 用;一般不改)。
