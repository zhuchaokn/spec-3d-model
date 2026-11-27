# 中国地形拼图 · 京津冀飞地完整合件版

2026-11-26 将北三县（三河、大厂、香河）连片区域及京津冀内部另一处河北飞地并入活动合件，沿用河北象牙白颜色并恢复缓存 DEM 地形。共用底层连续，两个孔消失；底座对应凸台降为槽底。只更新京津冀合件和第 5 盘底座，其余可沿用；圆头接口保持 0.12 mm 公差。新修改尚待实物试打。

## 当前交付

- `output/china_relief_P2S_9plates_hebei_exclaves_sliced.3mf`：全部九盘已切片，约 82 MB。
- `output/china_relief_P2S_9plates_hebei_exclaves.3mf`：可编辑九盘工程，约 15 MB。
- `output/china_relief_hebei_exclaves_multicolor.blend`：装配位置的彩色模型。
- `output/china_relief_hebei_exclaves.blend`：闭合单实体模型。
- `output/hebei_exclaves/`：33 份毫米 STL，四片底座、27 份单省、两组合件。STL 不携带多色信息，多色打印使用 3MF。
- `output/china_relief_round_paddle_012mm_test_sliced.3mf`：真实圆头轮廓裁成的灰色试配件，约 2.84 g，独立于九盘正式工程；也提供同名未切片 3MF 与公母 STL。

旧版文件与南海 50 mm 深嵌色小样保留。MakerWorld 草稿不随本次修订自动更新。

## 结构与打印

尺寸、配色与设置在 `model.json`；接口说明见 `spec/joints_and_assemblies.html`。

- 地图宽 430 mm，Albers 等积投影，高程统一放大 40 倍，不对单省归一化。台湾、海南主岛仍可独立拆下。
- 底座组装尺寸 470 × 470 mm，四片最大约 247 × 247 × 7 mm，适合 P2S 256 mm 打印床；外角 R5 mm，边框保留。
- 四条内接边各两个粗颈圆头，共八个。颈宽 8 mm、圆头直径 12 mm、伸出 12 mm，过渡 R0.6 mm；母槽沿配合轮廓法线外扩 0.12 mm，直线接缝 0.1 mm。**从上方向下落入组装**，防止底座在平面方向拉开。本次接口不变。
- 京津冀共用 1.6 mm 连续象牙白底层：河北象牙白、北京绿色、天津黄色；江苏上海共用同厚底层：江苏象牙白、上海橙色。省份上表面高程保留。最终为 29 份活动地图件，京津沪不再单独打印。
- 国境/海岸轮廓槽深 2 mm，底厚 2 mm，轮廓每侧外扩 0.15 mm；省份切片轮廓补偿 -0.08 mm。平台高 4 mm，边框高 7 mm、宽 5 mm。
- 主图固定小岛齐平且灰色；真实海洋蓝色皮层 Z=3.6–4.0 mm，邻国陆地灰色。
- 南海附图象牙白深嵌色 Z=2.8–4.0 mm，共六层，下方连续灰色承托；线宽和极小岛符号最小宽 1 mm，标题 5.5 mm，群岛名/比例说明 4.5 mm，笔画加粗 0.08 mm。全部 191 个源组件、99 个南沙组件与 10 段示意线保留。
- 第 1 盘两组多色合件，第 2–5 盘底座，第 6–9 盘同色单省。各盘实体数 2 / 1 / 1 / 1 / 1 / 6 / 7 / 7 / 7。第 1 盘象牙白、绿、黄、橙四色，可由四槽 AMS 打印。
- 六色编号：1 灰、2 蓝、3 象牙白、4 绿、5 黄、6 橙。5% gyroid、2 道墙、4 层顶壳/3 层底壳，**擦料塔关闭**，官方废料槽冲刷保留。底座 0.20 mm、省份 0.16 mm，首层 0.20 mm。

九盘已通过 Bambu Studio 2.6 CLI 切片，估算总耗材 **896.10 g**，含第 1 盘正式合件和正常换色冲刷，另加圆头小样 2.84 g。新底座与两组合件无浮空警告；保持原样的湖北仍有原切片器浮空提示，见 `spec/flush_slice_report.json`。未发送打印任务。

## 数据与验证

- 省界：[阿里 DataV](https://geo.datav.aliyun.com/areas_v3/bound/100000_full.json)，按 GCJ-02 候选转换 WGS84；原文件未声明 CRS，不宣称权威测绘精度。再分发许可未核实，仓库不包含原始边界文件。
- 高程：[AWS Terrain Tiles](https://registry.opendata.aws/terrain-tiles/)，实际瓦片 GMTED2010 / ETOPO1、zoom 6，URL、哈希与署名在数据清单中。
- 海岸：[Natural Earth 1:50m land](https://www.naturalearthdata.com/downloads/50m-physical-vectors/50m-land/)，公有领域。南海附图是独立比例，极小符号为可打印性放大。

`spec/dovetail_assembly_verification.json` 核对实际底座底面与圆头轮廓、八组圆弧和颈部配合面的实测 0.12 mm 距离、两组单连通闭合实体、保留 27 单省网格/颜色/变换、九盘数量与床面范围。合件色块上表面顶点与原始数据一致，共用底层与各色体积闭合分区。构建时仅清理体积小于 1e-6 mm³ 的内部接触薄片，不补洞或吞并有效小岛。

Blender 和 STL 的 33 个实体均水密、绕向正确、正体积；最终 3MF 的 47 个色块网格也通过相同检查。`spec/flush_slice_report.json` 核对九盘 G-code 的 MD5、P2S 型号、层高、六层南海嵌色、5% 填充与关闭擦料塔。`spec/recess_report.json` 和 `spec/sea_color_report.json` 验证槽与真实海陆分色。`spec/slice_preservation_report.json` 按对象名核对已切片工程，确认 CLI 重编号后几何位置、颜色、设置和分盘仍与可编辑工程一致。`spec/hebei_exclave_verification.json` 验证两处孔已填入连续底层、底座相应位置为 2 mm 槽底且没有凸台、原河北高程顶点完全保留，31 个其他打印实体逐字节不变。未截图或渲染。

## 复现本次修订

在已有完整数据缓存和上一版圆头九盘工程的项目内运行。参数与包含飞地的代码范围在 model.json。prepare_hebei_exclaves.py 用原省界归属识别被京津冀包围的河北地区，从 terrain_mosaic.tif 恢复高程，不重新下载或重采样原主省份。原河北主块保存为 primary_mesh_file，重复运行不会重复叠加飞地。

```sh
python tools/prepare_hebei_exclaves.py
python tools/prepare_province_assemblies.py
python tools/revise_tray_depth.py
python tools/recolor_bases.py
python tools/revise_nine_plate_project.py output/china_relief_P2S_9plates_round_paddle_012mm.3mf output/china_relief_P2S_9plates_hebei_exclaves.3mf --include-assembly A_京津冀 --include-base Tray_X2_Y2
python tools/verify_hebei_exclaves.py output/china_relief_P2S_9plates_round_paddle_012mm.3mf output/china_relief_P2S_9plates_hebei_exclaves.3mf
blender --background --factory-startup --python run_model.py
blender --background --python tools/color_blender.py
python tools/verify_exports.py
python tools/verify_recess.py
```

用 Bambu Studio CLI 对新工程执行 --slice 0 --export-3mf，再用 tools/finalize_revision_slice.py 规范化 P2S 元数据并核对九盘 G-code。tools/verify_slice_preservation.py 按对象名核对最终切片文件与模型源的几何、配色和摆盘。本轮输入在 output/hebei_exclave_backup/；旧工程、圆头试配小样和南海实图小样保留，不占新增正式盘。模型二进制保留本地 output，数据缓存与原始省界不随源码再分发。

北三县在省界数据里为一个连片区域；本次合件内部恢复两处属于河北的飞地（约 9.95 mm²、1.03 mm²）。采用 1.6 mm 连续共用底层，顶面仍取真实 DEM 海拔。对应底座的凸台取消，槽底厚 2 mm、槽深 2 mm；京津冀底面没有穿孔。河北外围极小沿海固定部件保持原样。
