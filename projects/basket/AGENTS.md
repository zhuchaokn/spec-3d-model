# basket — 纸样收纳筐

> spec-3d-model 的第一个试点(引擎驱动)。方法论见仓根 `CLAUDE.md`,引擎用法见 `lib/ENGINE.md`。

## 目标

3D 打印一个存放衣服纸样的敞口收纳筐,外形 29×20×20cm,四壁+底六边形镂空,
前后长墙下凹、两侧短墙带把手。因超 Bambu P2S 打印体积(256³mm),沿 X 切成左右两半,
用 C夹 + 圆台 Pin 卡合连接。

## 关键尺寸

外形 29(X)×20(Y)×20(Z)cm,壁厚 3mm。详值见 `model.json` 的 `constants`(唯一真相源)。

## 结构

```
spec/requirement.md   需求
spec/preview.html     三视图(⛔ 方案闸门,人确认后才写 model.json)
model.json            唯一真相源:常量 + 对象拓扑
run_model.py          在 Blender 里跑构建
ops/                  本项目专属 op:hex_array / scallop / cclip
output/               产物 BasketL/BasketR.stl + basket.blend(gitignore)
screenshots/          迭代截图存档
```

## 构建策略(model.json 里的节点顺序)

**独立构建每一半、再配卡合、不 union、最后拉开。** 左半配 Pin、右半配 C夹。
Pin 为圆台(底 φ5.12 / 顶 φ5.0,从下往上滑入楔紧)。卡合件是**独立对象**,只是摆在
与筐半重叠的位置(不合并——易拆、天然水密);打印时同一半的筐+卡合件一起导出到一个 STL。

| 阶段 | 节点 | 做什么 |
|---|---|---|
| 精建左半 | `BasketL` → `_cavity` → `_hex` → `_scallop` → `_handle` | 建壳 → 挖腔 → 六边形镂空 → 前后墙凹沿 → 左短墙把手 |
| 镜像右半 | `BasketR` | `mirror` BasketL(此时只有壳,尚无卡合件)得对称右半 |
| 底板让位 | `FootCut*` | 复制 C夹当切割器、放到 pin 位置(缝中心)、挖 BasketL 底板缝端,让 C夹能套入 |
| 卡合件 | `PinLF/PinLB`(左)`CClipRF/CClipRB`(右) | 缝处前后墙各一套,独立摆放 |
| 分件 | `SpreadL/SpreadR` | 各半连同其卡合件整组沿 X 拉开 |
| 导出 | `Export` | 每个可打印件(筐半+其卡合件)导出一个 STL + 存 .blend |

> 关键坐标:缝在 x=0;C夹圆心相对 pin 外移 `CCLIP_OFFSET`(=JOINT_R−0.2)避开墙;
> 卡合柱顶 = 凹沿最低点 `JOINT_TOP`。工程细节(切割器探出、hex 先于 scallop 等)见 `lib/ENGINE.md` 常见坑。

## 约定

- 尺寸/公差只改 `model.json` 常量;`spec/preview.html` 镜像它。
- 数据验证优先(`scene_dump`/`manifold_report`,判据:边界边=0),不随意截图。
- 正式拆分打印前,建议先打 C夹+Pin 试配小件定死公差。

## 来源

参数取自早期真机验证过的单体解法(墙3mm、六边形 pointy-top、C夹 φ9/孔 φ5.12、
Pin 圆台 φ5.12→5.0)。本项目用引擎按对象拓扑重构,已跑通并可导出打印。
