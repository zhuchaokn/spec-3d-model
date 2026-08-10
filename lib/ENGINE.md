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
# server 注入 __file__,LIB 从脚本位置反推(projects/<名> → 仓根 → lib),不写死
PROJ = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(os.path.dirname(os.path.dirname(PROJ)), "lib")
if LIB not in sys.path: sys.path.insert(0, LIB)
import s3d, engine
importlib.reload(s3d); importlib.reload(engine)          # 命名空间每次全新,必须 reload

import bpy
for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)  # 清场
s3d.set_cm_units()
engine.run_model(os.path.join(PROJ, "model.json"), lib_dir=LIB)
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
- **虚拟节点当参照系**:当参照系不是一个真实物体(如一个整体盒子的某一面墙,并非独立 object),
  用 `op:null` 节点把这面墙表达成一个参照系(`parent=Box, offset=[0, W/2-WALL/2, 0]` 即墙中心),
  子节点再挂到它上面。逐级 `相对+参照` 叠加,即可精确定位到墙上的特征。
- `s3d.py` 有坐标助手:`rel_to_abs / box_corner / face_center / wall_center`。

---

## 常见坑(务必遵守)

1. **★ 切割器要"做大、探出",绝不与被切面刚好齐平(共面)。** 这是布尔减法的核心套路:
   切割器**不必**等于要减掉的那块,可以在**不会伤到需保留部分**的方向上任意做大,只要每个
   切穿方向都**超出**实体。齐平/共面会产生退化面 → 残面或真漏洞。
   - 例(截柱顶):要把 5×5×10 柱体上面 3cm 截走,别用 5×5×3 刚好盖住;用个 10×10×10
     的大盒,向上移到"底面落在 z=7"的位置,再 `subtract`。四周和顶都大幅探出,底面切口干净。
   - 好处:除干净无副作用外,**大盒的质心/相对坐标更好算**——你只需让它的一个面落在切割线上,
     其余尺寸随便大。这正是相对坐标能力的核心应用:切割器 `parent`=被切件(或其虚拟子面),
     `offset` 只需把那个关键切割面对齐,尺寸给足即可。
2. **顺序影响布尔正确性。** 同一对象上多个切割,若后一个依赖前一个留下的材料,顺序错会吃穿——
   用 `after` 显式排序。
3. **少用 union,零件独立摆在重叠位置即可。** 配合的两个件(如插销与卡座)**不要 bool 合并**,
   各自作为独立闭合对象、摆在重叠/接触的位置就行。理由:①合体好合、拆开难拆,后续调整不便;
   ②合并会在交界产生非流形、甚至真漏洞;③独立件各自天然水密。
   打印时同一可打印件的多个重叠对象**一起导出到一个 STL**,切片器自动合并(见 `export` op)。
   移动/拉开这类件时要**整组一起移**(`move` 支持 `names` 多对象)。
4. **对称件用 `mirror` 不重复声明**;镜像要在加不对称特征**之前**做(否则不对称特征也被镜像)。
5. **拆件用 `move` 拉开**,避免分件缝处重叠。
6. **水密判据 = 边界边为 0,不是非流形为 0。** 用 `s3d.manifold_report`:
   - 边界边(<2面)= 真漏洞,**必须 0**;
   - 非流形(>2面)= T 形自交线(如圆柱穿过平面墙),切片器容忍,不用清零。
7. **每次全量构建先清场**(见 run_model.py 模板)。
8. **数据验证优先,少截图。** 用 `scene_dump`/`inspect`/`bbox`/`manifold_report` 核对;
   只有视觉缺陷(如镂空是否切透、整体形态)才截图,且存 `projects/<名>/screenshots/` 不丢。

> 以上每条都在 `projects/basket` 里有真实印证——想看具体数值/案例,读那个项目。

---

## 相关文件

- `lib/engine.py` — 引擎实现。
- `lib/s3d.py` + `lib/README.md` — 原子(建模/坐标/读场景/诊断)。
- `lib/ops/` + `lib/ops/README.md` — 通用 op 及其契约。
- `projects/basket/` — 完整实例(可参照它写新项目)。
- 新建项目的完整流程、设计原则 → 仓根 `CLAUDE.md`。
