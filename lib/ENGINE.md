# 构建引擎使用手册

> 给 Agent 的说明书。这是 spec-3d-model 的几何构建引擎:你写一份 JSON 描述"要建哪些
> 物体、多大、在哪、怎么建",引擎在 Blender 里把它建出来。**你几乎只需要写 JSON。**

---

## 这是什么

- **一份 JSON = 唯一真相源**:声明常量 + 对象拓扑(每个物体的尺寸、参照谁、相对坐标、用哪个 op)。
- **引擎 = 纯调度器**:读 JSON → 求值表达式 → 算出每个物体的绝对坐标 → 按依赖顺序 → 逐个调用 op 脚本建模。引擎不懂任何具体形状。
- **op = 一段建模逻辑**(建盒/挖孔/圆台/镜像…),`lib/ops/` 是通用的,`projects/<名>/ops/` 是项目专属的。
- **改设计 = 改 JSON 数据**,不动代码。

```
projects/<名>/model.json ──▶ engine.run_model() ──▶ Blender 场景 + 导出 STL
```

---

## 快速上手

**1. 运行一个模型**(在 Blender 里,通过 `execute_blender_code`):

```python
# projects/<名>/run_model.py
import sys, importlib, os
LIB = "/Users/zhuchao14/blender/lib"
if LIB not in sys.path: sys.path.insert(0, LIB)
import s3d, engine
importlib.reload(s3d); importlib.reload(engine)          # 命名空间每次全新,必须 reload

import bpy
for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)  # 清场
s3d.set_cm_units()
engine.run_model(os.path.join(os.path.dirname(__file__), "model.json"), lib_dir=LIB)
```

**2. 最小 model.json**(建一个空心盒):

```json
{
  "constants": { "W": 10, "WALL": 0.3 },
  "nodes": [
    { "name": "Box", "op": "ops/box.py", "parent": null,
      "offset": ["0","0","W/2"], "params": { "size": ["W","W","W"] } },
    { "name": "Cavity", "op": "ops/subtract.py", "parent": "Box",
      "offset": ["0","0","WALL"], "target": ["Box"], "after": ["Box"],
      "params": { "size": ["W-2*WALL","W-2*WALL","W"] } }
  ]
}
```

跑完场景里就有一个名为 `Box` 的空心盒。想加特征就加节点(挖孔、镜像、导出…)。

---

## JSON 字段速查

顶层:`{ "constants": {...}, "nodes": [...] }`

### constants
名→值。值可以是数字,或**表达式字符串**(可引用其他常量):
```json
"JOINT_R": "JOINT_OD / 2",  "HALF": "L/2 - GAP/2"
```

### 每个 node —— 引擎只认这 7 个字段(其余忽略,`params` 整包透传给 op)

| 字段 | 必填 | 含义 |
|---|---|---|
| `name` | ✔ | 唯一标识,= 建出的场景对象名 |
| `op` | ✔* | op 脚本路径 `ops/xxx.py`;`null`=虚拟节点(不建模,只当坐标参照系) |
| `parent` | | **坐标**参照(单一,构成树)。`null`=根,`offset` 即世界绝对质心 |
| `offset` | | `[x,y,z]` 相对 parent 质心的**相对坐标**(cm,可表达式)。默认 `[0,0,0]` |
| `target` | | 依赖的其他节点名列表(可多)。引擎把它们的 `object`+`center` 塞进 `ctx.targets` 供 op 用 |
| `after` | | 纯**排序**依赖(可多),不传数据。用于同一对象上多个修改 op 的先后 |
| `params` | | 给 op 的参数(黑盒)。字符串/数字/列表都会先做表达式求值,非表达式字符串(如对象名)原样传 |

**三种依赖的区别**(关键):
- `parent` = 我的坐标以谁算(树)。
- `target` = 我这个 op 要**作用/读取**谁(如 subtract 减谁、mirror/export 处理谁)。
- `after` = 只保证先后,不给数据(如 `挖腔→镂空→凹沿→把手` 的顺序)。

---

## 引擎做什么(执行顺序)

`run_model()` 依次:
1. **求值 constants**(表达式,支持互相引用)。
2. **拓扑排序**:合并 `parent`+`target`+`after` 三种依赖边,排出建造顺序,检测环。
3. **resolve 坐标**:每个节点 `绝对质心 = offset + parent的绝对质心`(递归)。绝对坐标从不存,只算。
4. **逐节点调 op**:求值该节点 `offset`/`params` → 收集 `target` 的对象与坐标 → 组 `ctx` → 调 `op.run(ctx)`。虚拟节点(`op:null`)跳过。

---

## 通用 op(`lib/ops/`,任何项目可直接用)

清单见 **`lib/ops/README.md`**。速览:
`box`(建盒) `subtract`(盒切割减) `frustum`(圆台,可 union) `capsule_cut`(胶囊镂空)
`mirror`(跨X=0镜像) `move`(平移) `heal`(修网格) `export`(导STL+blend)。

项目专属 op 放 `projects/<名>/ops/`,`model.json` 一样用 `ops/xxx.py` 引用(项目优先,lib 回落)。
缺能力就写新 op:实现 `run(ctx)`(见 ops/README 契约),通用的进 lib、专属的进项目。

---

## 表达式(offset/size/常量里的字符串)

受限数学,安全够用:
- 常量引用、数字、`+ - * / ** %`、一元 `±`、括号;
- 函数:`sin cos tan sqrt abs min max floor ceil round radians degrees`;常量 `pi tau e`。
- **禁止**属性访问、任意函数、外部变量。复杂逻辑(阵列铺算等)不写进表达式,写进 op。

---

## 坐标模型(设计时的核心工作)

3D 建模 = 理清**有哪些物体、各自尺寸、各自坐标**,再拼接/布尔组合。坐标两套配合:
- **绝对**:世界原点基准,定位**质心**。给定质心+尺寸,任意角/面坐标可算。
- **相对**:以另一物体质心为原点。算"A 相对 B 在哪"极简。
- 换算:`绝对 = 相对 + 参照物质心`。先在相对系想清楚(好算),引擎 resolve 时转绝对(好画)。
- **虚拟节点当参照系**:没有独立物体的参照(如盒子的"前墙"),用 `op:null` 节点表达
  (`parent=Box, offset=[0, W/2-WALL/2, 0]`),子节点再挂它上面。逐级 `相对+参照` 叠加。
- `s3d.py` 有坐标助手:`rel_to_abs / box_corner / face_center / wall_center`。

---

## 常见坑(务必遵守)

1. **切割器要探出被切面,别共面。** 挖腔/开口的切割器在切穿方向要**超出**实体(如 cavity
   的 Z 满高再上移一个壁厚 → 敞口干净)。共面会留残面或切不透。
2. **共面会产生真漏洞。** 两个面精确同坐标(如柱顶 z=15 撞凹沿底 z=15)让布尔留退化缝。
   错开一点(柱顶 14.7)即消除。
3. **顺序影响布尔正确性。** 同一对象多次切割,后者依赖前者留的材料 → 用 `after` 排序
   (实测:镂空必须先于凹沿,否则凹沿先削顶、镂空再往空区切会吃穿整墙)。
4. **对称件用 `mirror` 不重复声明**;镜像要在加不对称特征(如卡合件)**之前**做。
5. **拆件用 `move` 拉开**,避免缝处重叠。
6. **水密判据 = 边界边为 0,不是非流形为 0。** 用 `s3d.manifold_report`:
   - 边界边(<2面)= 真漏洞,**必须 0**;
   - 非流形(>2面)= T 形自交线(如柱穿墙),切片器容忍,不用清零。
   卡合件 union 后跑一次 `heal` op 清可并残点。
7. **每次全量构建先清场**(见 run_model.py 模板)。
8. **数据验证优先,少截图。** 用 `scene_dump`/`inspect`/`bbox`/`manifold_report` 核对;
   只有视觉缺陷(镂空缺失、形态)才截图,且存 `projects/<名>/screenshots/` 不丢。

---

## 建一个新项目

1. `projects/<名>/`,拷 `run_model.py`(改 MODEL 指向)。
2. 写 `spec/requirement.md` 理清需求。
3. **手写等比例 `spec/preview.html` 三视图**(方案闸门,⛔ 停下与人确认)。
4. 写 `model.json`:列对象/尺寸/parent/offset/op —— 这是设计的核心。复用通用 op,缺则写项目 op。
5. `run_model` 跑 → `scene_dump`/`manifold_report` 数据验证 → 必要时截图。
6. 加 `export` 节点导出 STL + .blend 到 `output/`。

---

## 相关文件

- `lib/engine.py` — 引擎实现。
- `lib/s3d.py` + `lib/README.md` — 原子(建模/坐标/读场景/诊断)。
- `lib/ops/` + `lib/ops/README.md` — 通用 op。
- `projects/basket/` — 完整实例(参照它写新项目)。
