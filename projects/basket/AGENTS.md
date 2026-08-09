# basket — 纸样收纳筐

> 项目入口。方法论见仓根 `CLAUDE.md`。这是 spec-3d-model 的第一个试点项目。

## 目标

3D 打印一个存放衣服纸样的敞口收纳筐,外形 29×20×20cm,四壁+底六边形镂空,
前后长墙下凹、两侧短墙带把手。因超 Bambu P2S 打印体积,沿 X 切成左右两半,
用 C夹+Pin 卡合连接。

## 关键尺寸

外形 29(X)×20(Y)×20(Z)cm,壁厚 3mm。打印体积 256³mm。详值见 `params.py`。

## 结构

```
spec/requirement.md   需求
spec/preview.html     三视图(⛔ 方案闸门,人确认后才建 3D)
params.py             单一尺寸源
components/<part>/     各部件
assemble.py           按序组合
verify.py             数据验证
export.py             导出 BasketL/BasketR 的 STL + .blend
output/               产物(gitignore)
```

## 组件清单 + 构建顺序

**核心:独立构建每一半(含镂空),再加卡合,最后组合分隔。禁止先建整体再切。**
左半配 **Pin**、右半配 **C夹**。Pin 为**圆台**(底 φ5.12 / 顶 φ5.0)平滑楔入。

| 顺序 | 组件 | 契约(输入场景 → 输出具名对象) | 状态 |
|---|---|---|---|
| 1 | `left_half` | 空场景 → 建 `BasketL`:左半空心壳(X −14.5..0,墙3mm,x=0 切缝面敞开)+ 六边形镂空 + 前后墙凹沿(左段)+ 左短墙(−X)胶囊把手 | 待建 |
| 2 | `right_half` | → 建 `BasketR`:右半(X 0..14.5)+ 镂空 + 凹沿(右段)+ 右短墙(+X)把手 | 待建 |
| 3 | `pin` | 对 `BasketL` 前后切缝墙加**圆台 Pin**(底5.12/顶5.0,防脱楔紧),join 进 `BasketL` | 待建 |
| 4 | `cclip` | 对 `BasketR` 前后切缝墙加 C夹(墩φ9+孔φ5.12+朝外开缝),join 进 `BasketR` | 待建 |
| 5 | `layout` | 把 `BasketL`/`BasketR` 沿 X 分隔摆放(展示/导出;`SPLIT_SHOW_GAP`,导出前可置0对合) | 待建 |

构建顺序:`left_half → right_half → pin → cclip → layout`(assemble.py 按此序)。
每个 build.py 可独立跑;`left_half`/`right_half` 各自完整(自含镂空),可分别打印验证。

## 约定

- 尺寸只改 `params.py`;组件与 preview.html 镜像它。
- build.py 幂等(清 `Basket`/`BasketL`/`BasketR`/`Cutter*`/`Seam*`)、产出具名对象、末尾 print。
- 数据验证优先(dims/部件数/水密),不随意截图。
- 正式拆分打印前,先打 clip+pin 试配件定死公差(参考旧 `blender_scripts/objects/make_clip_tester.py`)。

## 来源

旧 `blender_scripts/objects/make_basket.py` 是本筐子的**单体解法**(已在真机验证)。
本项目把它按分层拆成上面 5 个组件,参数原样迁到 `params.py`。
