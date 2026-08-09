# spec-3d-model 构建引擎 · 权威方案

> 本文件描述**已实现并跑通**的构建引擎(以 basket 试点验证)。做新项目从这里上手。
> 引擎代码:`lib/engine.py`;原子:`lib/s3d.py`;操作:`lib/ops/*.py`;注册表:`projects/<name>/model.json`。

## 0. 一句话

**一份 JSON 注册表(唯一真相源:常量 + 对象拓扑),经一个纯调度引擎解析出绝对坐标、
拓扑排序后逐节点调用 op 脚本,在 Blender 里建出模型。** 改设计=改 JSON 数据,不动代码。

```
projects/<name>/model.json ──▶ engine.run_model() ──▶ Blender 场景
   (常量 + 节点拓扑)          求值·resolve·拓扑·调 op        (成品对象)
```

## 1. 三层职责(与仓库目录一致)

| 层 | 位置 | 职责 | 是否通用 |
|---|---|---|---|
| 引擎 | `lib/engine.py` | 纯调度器:表达式求值 + 坐标 resolve + 拓扑排序 + 调 op。**不懂任何形状/操作** | 通用 |
| 原子 | `lib/s3d.py` | 无业务的 bpy 原子:建盒/柱/圆台/棱柱/胶囊、布尔、清理、坐标助手、导出、读场景 | 通用 |
| 操作 | `lib/ops/*.py` | 一个 op = 一种"怎么建"的逻辑(box/subtract/frustum/hex_array/…)。统一签名 | 通用 |
| 注册表 | `projects/<name>/model.json` | 该项目**有哪些对象、各自尺寸、参照谁、相对坐标、调哪个 op**。唯一真相源 | 项目专属 |

**铁律**:形状/操作逻辑只进 op;尺寸/坐标/关系只进 JSON。引擎两者都不碰,只调度。
`params.py` 已废除——尺寸是对象的属性,归 JSON 常量与节点。

## 2. 执行模型(引擎做的四件事)

`engine.run_model(json_path)` 按序:

1. **求值常量** `resolve_constants`:JSON `constants` 段,支持常量间引用与表达式
   (如 `"JOINT_R": "JOINT_OD/2"`),反复扫描按依赖解析,检测循环引用。
2. **拓扑排序** `topo_order`:合并三种依赖边 → 有向图排序,检测环:
   - `parent`(单一)→ 坐标树
   - `target`(可多)→ 装配/布尔 DAG
   - `after`(可多)→ 纯排序(同一对象上多个修改 op 的先后)
3. **resolve 坐标** `resolve_center`:沿 parent 链累加 offset。**绝对坐标从不存,只算**:
   `abs(n) = offset(n) + abs(parent(n))`;根节点(parent=null)的 offset 即绝对锚(质心)。
4. **逐节点调 op**:求值该节点 `offset`/`params` 表达式 → 收集 `target` 的 `{object, center}`
   → 组 `Ctx` → 调 op 的 `run(ctx)`。虚拟节点(`op:null`)跳过,只当参照系。

### 命名空间/持久化前提(为何这样设计)

`execute_blender_code` 每次 `exec` 命名空间全新(无 `__file__`、无跨调用变量),但 **Blender
场景持续存在**。故:①对象间只经**场景里的具名对象**交接;②运行入口 `run_model.py` 头部
`importlib.reload(s3d, engine)` 让本地编辑生效;③每次全量构建先清场。

## 3. 注册表 JSON 结构(权威)

```jsonc
{
  "constants": {                    // 命名常量:数字或表达式字符串,可互相引用
    "L": 29.0, "WALL": 0.3,
    "JOINT_R": "JOINT_OD/2",        // 表达式:受限数学(见 §5)
    "CCLIP_OFFSET": "JOINT_R - 0.2"
  },
  "nodes": [
    {
      "name": "BasketL",            // 唯一标识(= 场景对象名)
      "op": "ops/box.py",           // op 脚本路径(相对 lib/);null=虚拟节点
      "parent": null,               // 坐标参照(单一);null=根,offset 即绝对质心
      "offset": ["-(HALF/2)","0","H/2"], // 相对 parent 质心的相对坐标(cm,可表达式)
      "target": ["BasketL"],        // 依赖的其它对象(可多);引擎 resolve 后连 object 塞进 ctx
      "after": ["BasketL_cavity"],  // 纯排序依赖(可多);不注入 ctx
      "params": { "size": ["HALF","W","H"] }  // 黑盒:表达式求值后原样喂 op
    }
  ]
}
```

**引擎只认这 6 个字段**:`name / op / parent / offset / target / params / after`(+`_note`/`_comment` 被忽略)。
其余全在 `params` 里透传给 op。这就是"逻辑与数据解耦"的落点:引擎词汇表极小且固定。

### parent vs target vs after(三种边,别混)

- **parent**=我的坐标以谁为原点算(单一,构成树)。
- **target**=我这个 op 要作用/依赖到谁(可多,构成 DAG);引擎把它们的 `object`+`center`
  放进 `ctx.targets`,op 才能拿到"要减的对象""连两件的两个对象"。
- **after**=仅保证先后,不传数据(如 cavity→hex→scallop→handle 顺序)。

## 4. op 脚本契约

```python
# lib/ops/xxx.py
import s3d
def run(ctx):
    # ctx.name    : 本节点名(= 产出对象名)
    # ctx.center  : 本节点绝对质心 (x,y,z) cm —— 引擎已 resolve
    # ctx.params  : 已求值参数 dict(数字/三元组/字符串)
    # ctx.targets : { dep_name: {"object": bpyObj, "center": (x,y,z)} }
    ...用 s3d 原子 + ctx 干活,产出/修改场景里的具名对象...
```

现有 op(`lib/ops/`):

| op | 作用 | 关键 params | target 语义 |
|---|---|---|---|
| `box` | 建具名长方体(实体) | `size=(x,y,z)` | — |
| `subtract` | 建临时盒切割器,从 target 布尔减 | `size` | 被减对象 |
| `frustum` | 建圆台(底/顶异径),有 target 则 union 进去 | `d_bot,d_top,h` | 并入的宿主 |
| `capsule_cut` | 胶囊镂空,从 target 减(把手) | `w,h,depth,axis` | 被减对象 |
| `scallop` | 长墙 `\___/` 凹沿梯形切割 | `L,W,H,dip,corner,flat,over` | 被切对象 |
| `hex_array` | 生成器:四壁+底铺 pointy-top 六边形,合并后一次布尔减 | `hex_w,gap,wall,margin_*,seam_side,seam_half,handle,scallop,full_L` | 被镂空对象 |
| `cclip` | 建 C 夹(墩−孔−缝)union 进 target | `od,id,slot_w,h,open` | 并入的宿主 |
| `mirror` | 跨 X=0 镜像 source 成新对象(翻法线) | `source` | — |
| `move` | 平移已存在对象(拉开两半) | `target_name,delta` | — |

新增能力=写个新 op(遵守 `run(ctx)` 签名),JSON 引用其路径即可,**引擎不改**。

## 5. 表达式求值(受限数学)

`offset`/`size`/常量的字符串按**受限数学表达式**求值(`engine.evaluate`,AST 白名单):
- 允许:常量引用、数字、`+ - * / ** %`、一元 `±`、括号;
- 白名单函数:`sin cos tan sqrt abs min max floor ceil round radians degrees`,常量 `pi tau e`;
- 禁止:属性访问、任意函数调用、名字空间外变量。安全且够用(全是坐标/角度计算)。

复杂逻辑(阵列铺算、轮廓生成)**不进表达式**,进 op 脚本。JSON 只表达数据 + 数学。

## 6. 坐标系统(设计时的核心工作)

见仓根 `CLAUDE.md`「坐标系统」。要点:
- **绝对**=世界原点基准,Blender 实际下刀、定位**质心**;**相对**=以另一物体质心为原点。
- 换算铁律 **`绝对 = 相对 + 参照物质心`**;先在相对系想清楚(好算),resolve 时转绝对(好画)。
- **虚拟节点**当参照系:如"前墙" `parent=Basket, offset=(0, W/2-WALL/2, 0), op:null`,
  卡合件再挂到墙上——一步步 `相对+参照绝对` 叠加,精确定位。
- `lib/s3d.py` 坐标助手:`rel_to_abs / box_corner / face_center / wall_center / vadd`。

## 7. 工程原则(basket 试点血泪换来的,务必遵守)

1. **切割器必须探出被切面,绝不共面。** 挖腔/开口/镂空的切割器要在切穿方向**超出**实体
   (如 cavity 的 X 满长再向缝侧移 WALL → 缝面全开;Z 满高再上移 WALL → 敞口)。共面会
   留残面(假"上盖")或切不透(孔不通)。
2. **构建顺序影响布尔正确性。** 同一对象上多个切割,若后者依赖前者尚存的材料,顺序错会
   吃穿。basket 实证:**hex 必须先于 scallop**(scallop 先削顶,hex 再往空区铺 cutter →
   合并布尔产生退化几何吃穿整墙)。用 `after` 显式排序。
3. **对称件用 mirror,不重复声明。** 建好一半的**壳**后镜像出另一半,再各自加卡合
   (镜像须在加卡合**之前**,否则卡合也被镜像)。保证对称、减重复。
4. **拆件用 move 拉开。** 分件打印的两半在缝处会产生非流形/重叠;`move` 拉开后各自独立,
   也符合打印现实。
5. **数据验证优先,截图仅在必要时且存档。** 默认用 `scene_dump`/`inspect`/`is_watertight`/
   `bbox` 核对尺寸/部件/水密。**只有视觉缺陷(镂空缺失、对称、形态)才截图**,且存进
   `projects/<name>/screenshots/` 不丢弃。
6. **隔离调试,不瞎猜。** 现象怪时,把可疑 op **单独跑在干净盒子上**、dump 每步 verts/dims/
   bbox,逐一排除(basket 定位吃穿 bug 即靠此:先证 bool_diff_many/prism/hex_array/scallop
   各自正常 → 锁定到顺序)。
7. **微调改 JSON 一处即可。** 引擎的价值:C夹移 2.5mm 只改一个 offset 常量,不动几何代码。
8. **每次全量构建先清场**,避免上次残留/调试对象污染。
9. **水密判据 = 边界边为 0,而非非流形为 0。** 用 `s3d.manifold_report` 区分:
   - **边界边(<2面)= 真漏洞,必须 0**——非 0 说明网格有洞,不可打印,须修。
   - **非流形边(>2面)= T 形自交线**(如卡合柱穿薄墙),切片器(Bambu/Cura)自动处理,**可容忍**。
   卡合件 union 完跑 `heal`(合并重复顶点)清掉可并的残点;剩余 T 交线交切片器。
   **共面碰撞是真漏洞的常见来源**:两个面精确同 z/同位会让布尔留退化缝
   (basket 实证:柱顶 z=15 撞凹沿底 z=15 → 2 个真漏洞;柱顶降到 14.7 避开即消除)。

## 8. 做一个新项目的步骤

1. `mkdir projects/<name>`,拷 `run_model.py`(改 PROJ/MODEL 路径)。
2. 写 `spec/requirement.md`(需求)+ **手写等比例 `spec/preview.html` 三视图**(方案闸门,
   ⛔ 停下与人确认)。见 CLAUDE.md 原则5。
3. 写 `model.json`:先列**有哪些对象、各自尺寸、参照谁、相对坐标、调哪个 op**(设计的核心工作)。
4. 复用现有 op;缺能力就写新 op(`run(ctx)` 签名)进 `lib/ops/`。
5. `run_model` 在 Blender 跑;`scene_dump` 数据验证;必要时截图存档。
6. `export`:导出各打印部件 STL + 保存 .blend 到 `output/`。

## 9. basket 现状 / 已知局限

- **水密:两半均 边界边=0(无漏洞,可打印)。** 剩非流形 T 交线(柱穿墙,L 67/R 135)交切片器。
- **卡合柱顶 = 14.7cm**:比凹沿最低点(15)矮 3mm,避开柱顶/凹沿底共面(否则留真漏洞)。功能无影响。
- **C夹墩探出墙外约 3mm**(BasketR Y 从 20→20.6):C夹墩 φ9 贴墙内侧鼓出。非缺陷(壳体镜像严格对称,
  两半 Z 均精确=20;dims 差异纯由 Pin 不凸 vs C夹墩凸所致)。若要外形规整可把墩往墙里收。
- 未做:`export`(STL/.blend 导出)op 化;布尔失败诊断/自愈;注册表 JSON schema 校验。按需迭代。
