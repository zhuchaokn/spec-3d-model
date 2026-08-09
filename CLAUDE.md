# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# spec-3d-model

用**工程化、分层分治**的方式构建 Blender 3D 打印模型的能力体系。类比 spec-coding:
先写规格、对齐方案,再分部件实现、组合成品。当前范围**仅 3D 建模(用于 3D 打印)**,
暂不涉及动画/材质/渲染。

## 核心思想:分层 + 分治

一个模型分三层,自底向上:

```
lib/                      第0层 · 原子能力  —— 通用 bpy 操作,与业务无关,跨项目共享
  s3d.py                    add_box / add_cylinder / prism / capsule / bool_* / join / export_stl ...
projects/<name>/          第2层 · 项目     —— 用组件组合出完整成品
  AGENTS.md                 项目入口:目标、结构、组件清单+构建顺序、约定
  params.py                 单一尺寸源:所有尺寸/公差常量
  spec/
    requirement.md          需求文字描述
    preview.html            正/左/俯三视图+尺寸标注(与人对齐方案、预演效果)
  components/<part>/       第1层 · 部件   —— 说明 + 脚本
    README.md               该部件的功能/尺寸/设计说明(给人看)
    build.py                Blender 脚本:幂等、产出具名对象、末尾 print 结果
  assemble.py               按组件顺序逐个 exec build.py → 一键全量构建
  verify.py                 数据验证(dims/bbox/部件数/面数/水密),不截图
  export.py                 导出各打印部件 STL + 保存 .blend 到 output/
  output/                   .blend / .stl(gitignore)
  screenshots/              仅人明确要求时保存的截图(入库,不随意丢)
```

原子(lib)→ 部件(component)→ 项目(project)。**原子不含业务,业务不写进 lib。**

## 执行模型(必读,决定了上面的架构)

`execute_blender_code(file_path=...)` 把文件内容发给 Blender addon,addon 执行
`exec(code, {"bpy": bpy})` 并把 stdout 返回。两个事实:

1. **Python 命名空间每次全新** —— 没有 `__file__`,上次的变量/import 都不在。
2. **Blender 场景 `bpy.data` 持续存在** —— 你上一次建的对象还在场景里;`sys.modules` 也持续缓存。

推论(硬约束):
- **组件之间只能通过"场景里的具名对象"通信**,不能靠 Python 变量传递。所以每个
  `build.py` 必须:①幂等(开头按名/前缀清理旧对象);②产出**具名**对象;③末尾 `print` 一行结果供判断成败。
- **共享库要 reload**:因 `sys.modules` 缓存,编辑了 `s3d.py`/`params.py` 后若不 reload,
  跑的还是旧代码。故 build.py 头部用固定 bootstrap:

```python
import sys, importlib
LIB = "/Users/zhuchao14/blender/lib"
PROJ = "/Users/zhuchao14/blender/projects/<name>"   # 换成本项目
for p in (LIB, PROJ):
    if p not in sys.path:
        sys.path.insert(0, p)
import s3d, params
importlib.reload(s3d); importlib.reload(params)      # 让本地编辑生效
from s3d import *
from params import *
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

有时参照系不是一个真实 object(如 BasketL 是一个整体 object,它的"前墙"并不是单独物体)。
这时**先算出虚拟参照物相对宿主的坐标**,再逐级换算:

- 例:BasketL 质心已知。其"前墙"相对框质心 = `(0, +W/2, 0)`(Y 边长 20 → 一半 10;后墙 `(0, -10, 0)`)。
  → 前墙绝对质心 = `BasketL质心 + (0,10,0)`。
- 再把 C夹/Pin 表达为"相对前墙质心"的坐标(见 `params.py` 的定位常量),
  → C夹绝对 = `前墙绝对 + C夹相对`。

一步步 `相对 + 参照绝对` 叠加,虚拟参照系照样能精确定位。设计文档要把这条链写清楚
(物体 → 参照系 → 相对坐标),它就是后续 Python 下刀和布尔的直接依据。

`lib/s3d.py` 提供坐标助手(`box_corner`/`face_center`/`rel_to_abs` 等)把这套换算固化下来。

## 原则

1. **分层分治**:原子/部件/项目各司其职;原子通用无业务,部件编码单个部件的设计意图,项目只做组合与顺序。
2. **场景即接口**:组件间只经具名对象交接。build.py 必须幂等、产出具名对象、末尾 print。命名有前缀(如 `Cutter*`/`Seam*`)便于清理。
3. **单一尺寸源**:所有尺寸/公差集中在 `params.py`。组件脚本与 preview.html 都**镜像**它,改数值只改一处。禁止在组件里硬编码尺寸。
4. **数据验证优先,不随意截图**:默认用几何**数据**验证(尺寸/bbox/部件数/面数/水密性)——视觉判断交给人。**除非人明确要求截图**,否则不调 `get_viewport_screenshot`;一旦获取,存进项目 `screenshots/` 并说明,不丢弃。
5. **先设计后实施,HTML 是权威规格**:动手建 3D 前,**手写**正交三视图 HTML(正/左/俯 + 等比例 + 尺寸标注)与需求文档,作为方案设计。改 HTML 远比改 3D 便宜——这是方案闸门。人确认后才写 Python 组件,且 Python **跟着 HTML/文档走**。HTML **直接手写**,不要写脚本去生成它(多余的间接层)。等比例:统一 px/cm 比例;镂空按真实铺阵画满每个有孔的面;卡合接口在相关视图里画出来。
6. **面向打印**:
   - 按**打印体积**拆件(如 Bambu P2S 256³mm),优先沿最长轴切分;
   - **FDM 友好**:避免大面积水平悬桥(如六边形用 pointy-top 尖顶朝上)、让孔轴顺层线;
   - **切缝避开孔**:分割面附近留"禁孔带"保实体,再加**卡合结构**(如 C夹+pin)连接;
   - **公差**:配合面留间隙(经验值 孔 φ5.12 / 柱身 φ5.0 滑配 / 柱底 φ5.12 过盈防脱,切面让位 ~0.15mm);
   - **先打试配件**:正式拆分大件前,先打小的配合测试件定公差。
7. **部件独立可构建**:每个 build.py 能单独跑迭代;assemble.py 负责按序一键全量。
8. **单位**:建模用 cm(`s3d.CM=0.01` 换算),场景显示设为 cm(`set_cm_units()`);Blender 内部仍是米。

## 工作流七步

1. **init** — 从 `templates/project/` 拷一份到 `projects/<name>/`,改 bootstrap 里的 PROJ 路径。
2. **requirement** — 把需求写进 `spec/requirement.md`,尺寸落到 `params.py`。
3. **设计:plan + HTML** — 定组件拆分与构建顺序,**手写**等比例 `spec/preview.html` 三视图作为方案规格。**⛔ 停下与人确认,再进入实施。**
4. **build** — 逐个写/跑组件 `build.py`,每个独立验证(数据)。
5. **assemble** — `assemble.py` 按顺序组合,得到完整成品。
6. **verify** — `verify.py` 数据核验(尺寸/部件/水密)。
7. **export** — `export.py` 导出各打印部件 STL + 保存 .blend 到 `output/`。

## 仓库现状

- `lib/` — 第0层原子(见 `lib/README.md`)。
- `templates/project/` — 空项目骨架,init 时拷贝。
- `projects/` — 各项目(第一个试点:`basket`)。
- `mcp/blender-mcp/` — BlenderMCP server(普通源码纳入,连通 Blender 用;一般不改)。
- `blender_scripts/` — 旧脚本库(保留不动,后续按新分层迁移)。
