# <项目名>

> 项目入口。init 后填写本文件。方法论见仓根 `CLAUDE.md`,引擎用法见 `lib/ENGINE.md`。

## 目标

<一句话:做出什么、给什么用途、什么工艺(3D打印机型/材料)。>

## 关键尺寸

<外形尺寸、打印体积约束。详值在 `model.json` 的 constants(单一真相源)。>

## 结构

```
spec/requirement.md   需求描述
spec/preview.html     三视图(方案闸门;数据镜像 model.json)
model.json            唯一真相源:常量 + 对象拓扑
run_model.py          在 Blender 里跑构建
ops/                  本项目专属 op(通用 op 用 lib/ops/)
output/               产物 .blend/.stl(gitignore)
screenshots/          视觉验证截图(入库)
```

## 对象拓扑(model.json 概览)

| 物体(node) | op | 说明 |
|---|---|---|
| `<Part>` | box | 整体外形 |
| ... | ... | ... |

## 流程(见 ENGINE.md §建新项目)

需求 → **手写三视图 HTML(闸门,人确认)** → 写 model.json → run_model 跑+数据验证 → export。

## 约定

- 尺寸只改 `model.json` 常量;preview.html 镜像它。
- 通用能力优先用 `lib/ops`;专属几何写 `ops/`。
- 数据验证优先(dims/漏洞/非流形),不随意截图。
