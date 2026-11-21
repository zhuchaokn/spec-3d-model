# 中国地形拼图 · 齐平嵌色 / R5 圆角版

2026-11-21 根据实物打印反馈修订。主图固定小岛不再凸起，南海附图岛礁、文字和示意线从凸起改为齐平多色嵌入，避免薄凸点容易被碰掉；整张底座的四个外角为 R5 mm 圆角。新结构尚未实物试打。

## 当前交付

- `output/china_relief_P2S_9plates_flush_inlays_R5.3mf`：约 13 MB 的可编辑模型工程，需要在 Bambu Studio 中切片。
- `output/china_relief_P2S_9plates_flush_inlays_R5_sliced.3mf`：含全部 9 盘 G-code，约 79 MB。
- `output/china_relief_flush_inlays_R5_multicolor.blend`：装配位置的彩色 Blender 模型。
- `output/china_relief_flush_inlays_R5.blend`：单体底座与省份的原始几何模型。
- `output/flush_inlays_R5/`：36 份毫米单位 STL，四片底座和 32 份省份。

旧版文件保留。MakerWorld 草稿不随本次修订自动更新。

## 结构与打印

所有尺寸、配色和打印设置均在 `model.json`。

- 地图宽 430 mm，Albers 等积投影；32 份活动省份包含海南主岛、台湾主岛。地形统一放大 40 倍，各省不单独归一化。
- 拼装底座 470 × 470 mm，分四片，最大 238 × 238 mm，适合 P2S 256 mm 打印床；内部拼接插舌位置保留。
- 国境、海岸轮廓槽深 2 mm，槽底厚 2 mm，每侧外扩 0.15 mm。平台高 4 mm，外围边框高 7 mm、宽 5 mm；省份切片轮廓补偿 -0.08 mm。
- 主图固定小岛与平台齐平，保持灰色。真正海洋的蓝色皮层从 Z=3.6 到 4.0 mm，邻国陆地灰色。
- 南海附图象牙白从 Z=3.6 到 4.0 mm，与蓝色层在 XY 中互斥，下方由连续灰色底材支承。源岛礁轮廓、文字、10 段示意线未移动或删除。
- 外角平面圆角 R5 mm，仅切除组装底座的四个外角，不圆整每片的内接缝。
- 保留用户保存的 9 盘：第 1 盘北京试配，第 2–5 盘四片底座，第 6–9 盘同色省份；四色各 8 省。六色编号：灰、蓝、象牙白、浅绿、黄、橙。
- 5% gyroid、2 道墙、顶部 4 层、底部 3 层，关闭擦料塔；官方 P2S 废料槽冲刷保留。底座 0.20 mm、省份 0.16 mm 层高。

全部 9 盘已通过 Bambu Studio 2.6 CLI 切片。四片修改后的底座无浮空警告。未改变的北京试配和湖北省仍有切片器的浮空提示，详见 `spec/flush_slice_report.json`。正式件估算 865.85 g，不含第 1 盘的 3.40 g 小样；这是切片估算，未启动打印。

## 数据与验证

- 省界：[阿里 DataV](https://geo.datav.aliyun.com/areas_v3/bound/100000_full.json)，按 GCJ-02 候选转换 WGS84；原文件未声明 CRS，不宣称权威测绘精度。再分发许可未核实，仓库不包含原始边界文件。
- 高程：[AWS Terrain Tiles](https://registry.opendata.aws/terrain-tiles/)，实际瓦片 GMTED2010 / ETOPO1，zoom 6。署名、URL 与哈希在 `data/raw/terrain_manifest.json` 及署名文件中。
- 海岸：[Natural Earth 1:50m land](https://www.naturalearthdata.com/downloads/50m-physical-vectors/50m-land/)，公有领域。南海附图是独立制图比例，极小符号为可打印性放大。

`spec/flush_revision_report.json` 核对齐平高度、实际嵌色底部的灰色支承、圆角移除范围、32 省网格哈希及 9 盘布局；`spec/recess_report.json` 检查各层表面面积与槽公差；`spec/sea_color_report.json` 检查真实海陆分色。Blender 与 STL 的 36 个实体均水密、绕向正确、正体积。未截图或渲染。

## 本次修订复现

在已有完整数据缓存和用户原 9 盘工程的项目内执行。`output/revision_backup/` 保存修订前模型、四片网格和省份哈希用于对比。不要运行旧的 `combine_plates.py` 重新摆盘。

```sh
python tools/revise_tray_depth.py
python tools/recolor_bases.py
python tools/verify_recess.py
python tools/verify_ocean_colors.py
python tools/revise_nine_plate_project.py output/china_relief_P2S_9plates_5pct_no_tower.3mf output/china_relief_P2S_9plates_flush_inlays_R5.3mf
python tools/verify_flush_revision.py output/china_relief_P2S_9plates_5pct_no_tower.3mf output/china_relief_P2S_9plates_flush_inlays_R5.3mf
blender --background --factory-startup --python run_model.py
blender --background --python tools/color_blender.py
python tools/verify_exports.py
```

用安装的 Bambu Studio CLI 对新工程执行 `--slice 0 --export-3mf`，再通过 `tools/finalize_revision_slice.py` 规范化 P2S 元数据并验证全部 G-code。安装依赖见 `requirements.txt`。没有缓存时先按来源清单获取原始文件，再运行 `tools/prepare.py` 和 `tools/prepare_ocean_mask.py`；全量重建受上游数据和字体版本影响，不用于替换本次已验证的省份。
