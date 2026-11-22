# 拓竹 AMS 四色顶针

保留17×15.5 mm椭圆指孔、14 mm环宽、1.6 mm基础环壁、22 mm凹碗扣面、2.4×1.0 mm盲坑及0.8 mm圆线。分色不改变外部轮廓，也不填堵扣眼。

| 耗材编号 | 区域 / 部件名 | 预览颜色 |
|---|---|---|
| 1 | 扣子 / Button_Ivory | 米白 #F2E8D5 |
| 2 | 指环与下部支撑 / Ring_LightGreen | 浅绿 #A8C89B |
| 3 | 四眼坑壁、坑底 / Eyes_DarkGreen | 深绿 #285943 |
| 4 | X 形线 / Stitches_Brown | 棕色 #9B633D |

四个材料体积组成一个装配体，共用坐标。扣子/指环色界位于扣面实体底部Z9.55 mm；扣眼采用向实体内0.6 mm的球壳色区。棕色优先覆盖凸线及扣眼内侧，分色切割器沿线的原始表面外扩0.02 mm，避免重合折面；实体尺寸与0.8 mm线宽保持原样。

## 在 Bambu Studio 中使用

1. 按项目打开`output/button_thimble_four_color.3mf`，保留一个装配体及四个部件；四眼是同一深绿部件内的四块区域。
2. 选择实际拓竹机型、喷嘴和打印配置。文件内包含导入所需的完整通用默认值与Generic PLA四色耗材信息，尚未选定实际机器或切片。
3. 将耗材1—4分别映射到AMS里的米白、浅绿、深绿、棕色。四路建议使用同一种材料类型，按实际线材修改耗材预设。
4. 已将共同Y指孔轴转为打印Z轴，并按整个扣面最低点落床。整体保留对齐，不单独自动摆放或拆成四个打印对象。
5. 已启用冲刷塔；切片后检查局部支撑、brim、冲刷塔位置与冲刷量。当前交付无G-code，未启动打印；最终支撑与冲刷量由实际设备、喷嘴和耗材确定。

单色`.stl`仍可单色打印；四色用`.3mf`，Blender编辑用`button_thimble_four_color.blend`。

## 验证与复现

入口仍为`run_model.py`：先生成并验收单色实体，再经JSON中的Multicolor节点分配材料体积。尺寸、色区厚度、配色、分色参数和文件名由`model.json`声明；原始凸线和分色切割器共享同一个圆线构造函数。

`multicolor_verification_report.json`检查四区闭合、六组两两重叠体积、总体积、包络和2053个原表面采样点覆盖；`ams_3mf_verification_report.json`独立读入归档中的毫米网格，检查每边恰两面共享、方向一致、退化面、连通块数及四路耗材映射。

导出只删除切片精度下严格零面积的三角面和严格重合反向成对面，不合并近点、不补洞。四色体积之和与原实体差约0.002 mm³，包络仍为22×22×22.614 mm。扣眼四个独立色区是预期结构。Bambu Studio 2.6已分别确认四区网格manifold=yes，并读取四色耗材列表。

`bambu_2p6_defaults.json`来自本机Bambu Studio 2.6 CLI的通用默认配置，不含用户的打印机或个人项目资料。Bambu项目导入需完整配置及有效的四色继承数组；该默认值用于格式兼容，实际打印配置在打开项目后选择。项目Application元数据采用Bambu兼容标识，以启用其耗材配置加载；Description注明由spec-3d-model生成。

```sh
python3 projects/lotus_thimble/tools/check_3mf.py \
  projects/lotus_thimble/output/button_thimble_four_color.3mf \
  --source-report projects/lotus_thimble/spec/multicolor_verification_report.json \
  --report projects/lotus_thimble/spec/ams_3mf_verification_report.json
```
