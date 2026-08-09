# 构建引擎设计(草案 · 待评审)

> spec-3d-model 的几何构建引擎。把「对象拓扑 + 相对坐标 + 命名常量」解析成绝对坐标,
> 再驱动 Blender 施工。**一份注册表,喂三个消费者:HTML 预览 / Blender 施工 / 场景验证。**
> 本文档只定设计,评审通过后再实现。引擎(通用)进 `lib/`,注册表(项目专属)在项目根。

## 1. 核心概念

- **对象 = 拓扑图节点。** 每节点存:`name`、`size`、`op`(实体/切割器)、`parent`、
  **相对 parent 的相对坐标 `offset`**、以及形状类型(box/cylinder/frustum/hex/capsule…)。
- **绝对坐标从不存储,只 resolve。** 沿 parent 链累加:`abs(node) = offset(node) + abs(parent)`。
  只有**根节点**需要一个绝对锚点(通常 world 原点或指定质心)。
- **虚拟节点**:不产生 mesh,只当参照系(如"前墙")。其 size/offset 由 parent 派生
  (`face_center`)。子节点挂它上面,坐标就好算。
- **常量**:给尺寸/公差/偏移取名字,让 offset 可读(`(0, WALL/2, 0)` 而非 `(0,0.15,0)`)。
  常量与对象**同处一份注册表**,是唯一真相源——废掉独立 params.py,消灭数字手抄。

## 2. 注册表(项目根 `model.py`)形态

Python 声明式(可 import、可内联表达式算尺寸、可 dump 成 JSON):

```python
# projects/basket/model.py —— 唯一真相源(对象拓扑 + 命名常量)
from engine import Node, Registry

# --- 命名常量(尺寸/公差/规则) ---
WALL = 0.3
L, W, H = 29.0, 20.0, 20.0
HEX_W, HEX_GAP = 2.5, 0.7
JOINT_OD, JOINT_ID = 0.9, 0.512
JOINT_R = JOINT_OD / 2
CCLIP_OFFSET = JOINT_R - 0.2         # 0.25
CLEAR_SLIDE = 0.012                  # 滑配间隙(孔-柱径差的一半语义)

R = Registry()
# 根:整筐(施工时按需切成 L/R,这里先给完整外形作参照锚)
R.add("Basket", shape="box", size=(L, W, H), parent=None, offset=(0,0,H/2))
# 虚拟墙:派生自 Basket 的面,当参照系
R.wall("FrontWall", parent="Basket", face="+y")   # 质心 = Basket + (0, +W/2, 0)
R.wall("BackWall",  parent="Basket", face="-y")
# 卡合件:相对"墙"定位(好算)
R.add("CClip_F", shape="cclip", size=(JOINT_OD, JOINT_ID, H*0.75),
      parent="FrontWall", offset=(CCLIP_OFFSET, 0, ...), op="solid", half="R")
R.add("Pin_F",   shape="frustum", size=(JOINT_ID, JOINT_ID-2*CLEAR_SLIDE, ...),
      parent="FrontWall", offset=(0, 0, ...), op="solid", half="L")
```

`Registry` 提供:`add()` / `wall()`(虚拟) / `resolve(name)->abs_center` / `dump()->list[dict]` /
`roots()` / `topo_order()`。

## 3. resolver(进 `lib/engine.py`,通用)

```
resolve(name):
    n = nodes[name]
    if n.parent is None: return n.offset            # 根:offset 即绝对锚
    return vadd(n.offset, resolve(n.parent))        # 相对 + 父绝对(递归/记忆化)
```

- 纯计算,**不依赖 bpy**,可离线跑 → HTML 和验证都能用。
- 拓扑排序 `topo_order()`:保证施工/resolve 按依赖顺序;检测环(设计错误)。
- 虚拟墙的 offset 由 `face` 自动算:`face='+y'` → `offset=(0, +size_parent.y/2, 0)`。

## 4. 施工(进 `lib/engine.py`,依赖 bpy)

`build(registry)`:按 `topo_order` 遍历:
- **实体节点**(`op="solid"`):按 shape 调 s3d 原子(`add_box`/`add_cylinder`/frustum…)
  在 resolve 出的绝对质心建具名对象。
- **切割器节点**(`op="subtract"`):建临时体 → 对 `target` 做 `bool_diff` → 删。
- **虚拟节点**:跳过(不建 mesh)。

## 5. 切割器如何表达?——两种画法(此处请评审拍板)

切割器不是成品,是"对某实体做布尔减"的操作。它也是几何体(有坐标/尺寸),
问题是**要不要进注册表拓扑**。

### 方案 A:切割器 = 拓扑节点,带 `op` 与 `target`

```python
R.add("HandleCut_L", shape="capsule", size=(8,4,2*WALL),
      parent="LeftWall", offset=(0,0,-HANDLE_GAP_TOP-...),
      op="subtract", target="Basket")      # ← 声明:减到 Basket 上
```
施工遇到 `op="subtract"` 的节点:建临时体 → `bool_diff(target, tmp)` → 删。

- ✅ 一份拓扑装下**全部几何意图**(成品+镂空),坐标同源、HTML 能一并画出孔位、
  验证能核对"该减的都减了"。切割器坐标也走 resolve,享受相对坐标红利。
- ✅ 布局规则(六边形阵列)可由一个"生成器节点"展开成多个 cutter 子节点。
- ⚠️ 注册表更大;需定义 `op`/`target` 语义;布尔顺序依赖 topo。

### 方案 B:注册表只放实体成品,切割器留在组件 build.py

```python
# 注册表只有 Basket / BasketL / BasketR / CClip / Pin 等成品
# 六边形、凹沿、把手的 cutter 在 components/honeycomb/build.py 里当局部逻辑
```

- ✅ 注册表小而纯(只答"有哪些成品、在哪")。
- ❌ 镂空的坐标/尺寸又散回 build.py,**与"唯一真相源"背道而驰**;HTML 要单独再表达一次孔位
  (又是手抄风险);验证无法从注册表核对镂空。

### 我的倾向

**方案 A**。理由:引擎的价值正是"所有几何意图同源可解析";把镂空踢出去,等于把最容易出错、
最需要 HTML 预演的部分(孔位/让位)重新散落——这正是我们要根治的病。代价(注册表变大、
需 op/target 语义)是值得的,且能用"生成器节点"控制规模。

## 6. 三消费者同源

```
              ┌──────────────┐
   model.py → │  Registry     │ → resolve() 绝对坐标(纯计算)
  (唯一真相)   └──────────────┘
                    │
        ┌───────────┼─────────────┐
        ▼           ▼             ▼
   HTML 预览     Blender 施工    场景验证
  (读坐标画图)  (建体+布尔)   (scene_dump ↔ resolve 比对)
```

- **HTML**:从 `dump()` 拿节点坐标/尺寸画三视图 —— 再不会漏抄常量(C夹消失病的根治)。
- **施工**:`build(R)` 一键;或组件按 topo 分段跑。
- **验证**:新增 `scene_dump()`(读真实场景全部对象的质心/尺寸/层级)与 resolve 结果比对;
  即使人手改了 Blender,也能读回真实态核对。

## 7. 需要补的 lib 能力

- `lib/engine.py`:`Node`/`Registry`/`resolve`/`topo_order`/`build`。
- `lib/s3d.py`:补 `scene_dump()`(读全场景 → list[dict]);补 frustum(圆台)原子
  (Pin 用,底/顶不同径);cclip 若做成 shape 也在此加"环−缝"构造。

## 8. 待评审决策

1. **切割器表达:方案 A(拓扑节点带 op/target) vs B(留在 build.py)** —— 我倾向 A。
2. 六边形这类**阵列**:用"生成器节点"在 resolve 时展开成多个 cutter(A 之下),可否?
3. 根锚点:整筐 `Basket` 作参照根,施工阶段再切 L/R;还是直接以 `BasketL`/`BasketR` 为两个根?
   (关系到"独立建每半"的组件顺序如何映射到拓扑)
