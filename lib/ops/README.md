# lib/ops/ — 全局通用 op(公共能力)

这里是**跨项目复用、与具体产品无关**的 op。任何 `model.json` 都能直接引用它们:
`"op": "ops/<name>.py"`。引擎按"项目目录优先 → lib 回落"查找,所以项目里没有同名 op 时
自动用这里的。

> 业务专属 op(编码某产品设计意图的,如筐子的六边形阵列)放在 `projects/<name>/ops/`,不进这里。

## op 契约(所有 op 统一)

```python
def run(ctx):
    # ctx.name    : 本节点名(= 产出对象名)
    # ctx.center  : 本节点绝对质心 (x,y,z) cm(引擎已 resolve)
    # ctx.params  : 已求值参数 dict
    # ctx.targets : { 依赖名: {"object": bpyObj, "center": (x,y,z)} }
```

## 可用 op 清单

| op | 作用 | params | target 语义 |
|---|---|---|---|
| `ops/box.py` | 建具名长方体(实体) | `size=[x,y,z]` | — |
| `ops/subtract.py` | 建临时盒切割器,从 target 布尔减 | `size=[x,y,z]` | 被减对象(可多) |
| `ops/frustum.py` | 建竖直圆台(底/顶异径,独立实体) | `d_bot,d_top,h`(可选 `seg`) | — |
| `ops/capsule_cut.py` | 胶囊镂空(中间矩形+两端半圆),从 target 减 | `w,h,depth,axis`('x'/'y'/'z') | 被减对象(可多) |
| `ops/copy.py` | 复制已存在对象为新对象、放到 ctx.center(常用来复制现成件当一次性切割器) | `source` | — |
| `ops/cut.py` | 用一个**已存在对象**当切割器从 target 布尔减,减完删切割器 | `tool` | 被减对象(可多) |
| `ops/mirror.py` | 跨 X=0 镜像 source 成新具名对象(翻法线) | `source` | — |
| `ops/move.py` | 平移一批已存在对象(拉开分件/摆放) | `names=[...]` 或 `target_name`,`delta=[dx,dy,dz]` | — |
| `ops/heal.py` | 合并重复顶点+重算法线,修布尔残边;报告 边界边/非流形 | `target_name`(可选 `dist`) | — |
| `ops/export.py` | 各可打印件导出 STL + 存 .blend | `pieces={文件名:[对象名...]},out_dir?(默认"output",相对项目),blend_name?` | — |

## 单位与约定

- 所有尺寸 **cm**;引擎/`s3d.CM=0.01` 换算到 Blender 内部米。
- 坐标定位的是**质心**。`offset` 是相对 parent 质心的相对坐标(见 `../ENGINE.md`)。
- op 内部用 `s3d.py` 原子(`add_box/add_cylinder/add_frustum/bool_diff/bool_union/...`,见 `../README.md`)。

## 加新通用 op

写 `lib/ops/<name>.py`,实现 `run(ctx)`,首行 docstring 写清作用,然后**在本表加一行**。
判据:跨项目、无业务(如"倒角""阵列复制")才进这里;编码某产品意图的进项目 ops。
