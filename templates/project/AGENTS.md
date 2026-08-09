# <项目名>

> 项目入口。init 后填写本文件。方法论见仓根 `CLAUDE.md`。

## 目标

<一句话:这个项目要做出什么、给什么用途、用什么工艺(3D打印机型/材料)。>

## 关键尺寸

<外形尺寸、打印体积约束。详值在 `params.py`(单一尺寸源)。>

## 结构

```
spec/requirement.md   需求描述
spec/preview.html     三视图(方案闸门)
params.py             单一尺寸源
components/<part>/     各部件(README + build.py)
assemble.py           按序组合
verify.py             数据验证
export.py             导出 STL + .blend
output/               产物(gitignore)
```

## 组件清单 + 构建顺序

| 顺序 | 组件 | 契约(输入场景 → 输出具名对象) | 状态 |
|---|---|---|---|
| 1 | `<part>` | 空场景 → 建 `<Obj>` | 待建 |
| 2 | ... | 对 `<Obj>` ... | 待建 |

构建顺序:`<part1> → <part2> → ...`(assemble.py 按此顺序 exec)。

## 约定

- 尺寸只改 `params.py`;组件与 HTML 镜像它。
- build.py 幂等、产出具名对象、末尾 print。
- 数据验证优先,不随意截图。
