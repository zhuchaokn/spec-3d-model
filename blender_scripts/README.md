# Blender Scripts Library

BlenderMCP 的脚本库。每个 `.py` 是一个**独立、可复用、幂等**的 Blender 操作，通过 `execute_blender_code(file_path=<绝对路径>)` 执行。

核心理念：**累积**。脚本用完不删，沉淀成本库，后续不断复用与改进——别每次都从零写。

## 运行方式

blender-mcp 的 `execute_blender_code` 接收 `file_path`（绝对路径），server 读取文件内容发给 Blender addon 执行，addon 的 stdout 作为结果返回给调用方。

1. 先开 Blender 并启动 BlenderMCP addon（监听 `localhost:9876`）。
2. agent 编辑某个脚本顶部的常量（参数），再用 `execute_blender_code(file_path=...)` 跑。
3. 比把整段代码塞进工具参数省 token —— 脚本留在本地，反复复用。

示例：

```
execute_blender_code(file_path="/Users/zhuchao14/3dmodel/blender_scripts/primitives/make_box.py")
```

## 目录约定

```
blender_scripts/
  README.md      本文件：用法与规范
  INDEX.md       脚本索引：每个脚本干啥、参数、输出（增删脚本后必须同步）
  _template.py   新脚本模板
  primitives/    建几何体（box/sphere/cylinder/plane...）
  objects/       复合建模对象（basket/shelf/盒盖...）
  scene/         场景查询（list/info/stats...）
  materials/     材质/着色
  transforms/    移动/旋转/缩放/apply
  io/            导入导出（glb/obj/stl/fbx）
  render/        渲染
```

新类别按需创建，命名用复数名词。

## 脚本规范（agent 新增/改脚本必须遵守）

1. **一文件一职责**，文件名 `动词_名词.py`（make_box、list_objects、apply_material）。
2. **顶部 docstring**：写清用途、是否幂等、输出格式。
3. **参数即顶部常量**：可调参数放文件最上方（`NAME` / `DIMENSIONS` / `LOCATION` 等），agent 改常量再跑，不要把参数硬编码进逻辑。
4. **幂等优先**：重跑不报错、不产生重复对象（创建前先删同名对象）。
5. **自包含**：只 `import bpy`（必要时加 math 等），不依赖外部状态或别的脚本。
6. **print 结果**：最后一行打印简洁结果（addon 把 stdout 返回给调用方），便于 agent 判断成败。
7. **同步 INDEX.md**：新增或修改脚本后，必须更新 `INDEX.md` 的表格 —— 这是累积索引，不同步就等于没沉淀。

## 新增脚本流程

1. 复制 `_template.py` 到合适的类别目录，改名（`动词_名词.py`）。
2. 填 docstring、顶部参数常量、逻辑、最后 `print` 结果。
3. 在 `INDEX.md` 表格加一行。
4. （可选但推荐）跑一遍验证。
