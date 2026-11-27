# 中国地形拼图 · 圆头接口 0.2 mm 版

2026-11-27 将底盘圆头母槽法线让位从 0.12 mm 增至 0.2 mm，公榫和 0.1 mm 直线缝不变。北三县等河北飞地完整合件、海拔、配色和 2 mm 凹槽保留。本次只需更新第 3–5 盘母槽底座，纯公榫第 2 盘和全部地图件沿用。0.2 mm 尚待实物试打。

## 当前交付

- `output/china_relief_P2S_9plates_hebei_exclaves_020mm_sliced.3mf`：全部九盘已切片，约 82 MB。
- `output/china_relief_P2S_9plates_hebei_exclaves_020mm.3mf`：可编辑九盘工程，约 15 MB。
- `output/china_relief_hebei_exclaves_020mm_multicolor.blend`：装配位置的彩色模型。
- `output/china_relief_hebei_exclaves_020mm.blend`：闭合单实体模型。
- `output/hebei_exclaves_020mm/`：33 份毫米 STL，四片底座、27 份单省、两组合件。STL 不携带多色信息，多色打印使用 3MF。
- `output/china_relief_round_paddle_020mm_test_sliced.3mf`：真实圆头轮廓裁成的灰色试配件，约 2.83 g，独立于九盘正式工程；也提供同名未切片 3MF 与公母 STL。

旧版文件与南海 50 mm 深嵌色小样保留。MakerWorld 草稿不随本次修订自动更新。

## 结构与打印

尺寸、配色与设置在 `model.json`；接口说明见 `spec/joints_and_assemblies.html`。

- 地图宽 430 mm，Albers 等积投影，高程统一放大 40 倍，不对单省归一化。台湾、海南主岛仍可独立拆下。
- 底座组装尺寸 470 × 470 mm，四片最大约 247 × 247 × 7 mm，适合 P2S 256 mm 打印床；外角 R5 mm，边框保留。
- 四条内接边各两个粗颈圆头，共八个。颈宽 8 mm、圆头直径 12 mm、伸出 12 mm，过渡 R0.6 mm；母槽沿配合轮廓法线外扩 0.2 mm，直线接缝 0.1 mm。**从上方向下落入组装**，防止底座在平面方向拉开。母槽由 0.12 mm 增至 0.2 mm，公榫不变。
- 京津冀共用 1.6 mm 连续象牙白底层：河北象牙白、北京绿色、天津黄色；江苏上海共用同厚底层：江苏象牙白、上海橙色。省份上表面高程保留。最终为 29 份活动地图件，京津沪不再单独打印。
- 国境/海岸轮廓槽深 2 mm，底厚 2 mm，轮廓每侧外扩 0.15 mm；省份切片轮廓补偿 -0.08 mm。平台高 4 mm，边框高 7 mm、宽 5 mm。
- 主图固定小岛齐平且灰色；真实海洋蓝色皮层 Z=3.6–4.0 mm，邻国陆地灰色。
- 南海附图象牙白深嵌色 Z=2.8–4.0 mm，共六层，下方连续灰色承托；线宽和极小岛符号最小宽 1 mm，标题 5.5 mm，群岛名/比例说明 4.5 mm，笔画加粗 0.08 mm。全部 191 个源组件、99 个南沙组件与 10 段示意线保留。
- 第 1 盘两组多色合件，第 2–5 盘底座，第 6–9 盘同色单省。各盘实体数 2 / 1 / 1 / 1 / 1 / 6 / 7 / 7 / 7。第 1 盘象牙白、绿、黄、橙四色，可由四槽 AMS 打印。
- 六色编号：1 灰、2 蓝、3 象牙白、4 绿、5 黄、6 橙。5% gyroid、2 道墙、4 层顶壳/3 层底壳，**擦料塔关闭**，官方废料槽冲刷保留。底座 0.20 mm、省份 0.16 mm，首层 0.20 mm。

九盘已通过 Bambu Studio 2.6 CLI 切片，估算总耗材 **896.06 g**，含第 1 盘正式合件和正常换色冲刷，另加圆头小样 2.83 g。新底座与两组合件无浮空警告；保持原样的湖北仍有原切片器浮空提示，见 `spec/flush_slice_report.json`。未发送打印任务。

## 数据与验证

- 省界：[阿里 DataV](https://geo.datav.aliyun.com/areas_v3/bound/100000_full.json)，按 GCJ-02 候选转换 WGS84；原文件未声明 CRS，不宣称权威测绘精度。再分发许可未核实，仓库不包含原始边界文件。
- 高程：[AWS Terrain Tiles](https://registry.opendata.aws/terrain-tiles/)，实际瓦片 GMTED2010 / ETOPO1、zoom 6，URL、哈希与署名在数据清单中。
- 海岸：[Natural Earth 1:50m land](https://www.naturalearthdata.com/downloads/50m-physical-vectors/50m-land/)，公有领域。南海附图是独立比例，极小符号为可打印性放大。

`spec/dovetail_assembly_verification.json` 核对实际底座底面与圆头轮廓、八组圆弧和颈部配合面的实测 0.2 mm 距离、两组单连通闭合实体、保留 27 单省网格/颜色/变换、九盘数量与床面范围。合件色块上表面顶点与原始数据一致，共用底层与各色体积闭合分区。构建时仅清理体积小于 1e-6 mm³ 的内部接触薄片，不补洞或吞并有效小岛。

Blender 和 STL 的 33 个实体均水密、绕向正确、正体积；最终 3MF 的 47 个色块网格也通过相同检查。`spec/flush_slice_report.json` 核对九盘 G-code 的 MD5、P2S 型号、层高、六层南海嵌色、5% 填充与关闭擦料塔。`spec/recess_report.json` 和 `spec/sea_color_report.json` 验证槽与真实海陆分色。`spec/slice_preservation_report.json` 按对象名核对已切片工程，确认 CLI 重编号后几何位置、颜色、设置和分盘仍与可编辑工程一致。`spec/hebei_exclave_verification.json` 验证两处孔已填入连续底层、底座相应位置为 2 mm 槽底且没有凸台、原河北高程顶点完全保留，该报告记录了飞地修订时其余 31 个实体不变。`spec/dovetail_clearance_revision_report.json` 验证本次只扩大母槽，30 个其他实体（29 份地图件和纯公榫底座）逐字节不变。`spec/color_welding_report.json` 记录毫米顶点归并后清理的 4 张零面积面；海面体积和尺寸在数值误差范围内保持一致。未截图或渲染。

## 复现本次修订

在已有河北飞地并入版数据缓存和九盘工程的项目内执行。只修改 model.json 的 TRAY_TAB_CLEARANCE，本次为 0.02 cm，即 0.2 mm；省形槽 SLOT_CLEARANCE 保持 0.015 cm。

```sh
python tools/revise_tray_depth.py
python tools/recolor_bases.py
python tools/revise_nine_plate_project.py output/china_relief_P2S_9plates_hebei_exclaves.3mf output/china_relief_P2S_9plates_hebei_exclaves_020mm.3mf --include-base Tray_X2_Y1 --include-base Tray_X1_Y2 --include-base Tray_X2_Y2
python tools/verify_dovetail_clearance_revision.py output/clearance020_backup/model.json output/china_relief_P2S_9plates_hebei_exclaves.3mf output/china_relief_P2S_9plates_hebei_exclaves_020mm.3mf
blender --background --factory-startup --python run_model.py
blender --background --python tools/color_blender.py
python tools/verify_exports.py
python tools/prepare_dovetail_coupon.py
```

用 Bambu Studio CLI 对正式工程和小样切片，再用 tools/finalize_revision_slice.py 核对 G-code（小样加 --dovetail-coupon）。本轮输入记录在 output/clearance020_backup/。原河北飞地版、圆头试配和南海实图小样保留。本次不重新生成省份地形、不修改河北飞地归属。
