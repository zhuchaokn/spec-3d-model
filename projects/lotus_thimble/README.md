# 椭圆指孔 · 四眼扣子顶针

按用户确认的莲蓬轮廓放大顶部，保留内收过渡、凹碗和厚圆唇；碗面改成四个圆底盲坑，增加两条微凸X形缝线。戴在左手食指，针托朝背侧。

## 当前尺寸与验证

- 指孔横向17 mm、竖向15.5 mm，沿Y贯通。
- 环身沿内椭圆法线等距加厚1.6 mm，环宽14 mm。局部填充支撑和扣面承力底部另行留厚。
- 顶部直径22 mm，按原14 mm莲蓬的22/14比例放大凹碗、厚边、圆唇和肩部；左右两侧改为单一R4.71大圆肩直接内收，去掉中上段S形鼓包；最内收半宽8.2 mm，Z6.25 mm附近。
- 四眼名义口径2.4 mm、深1.0 mm，圆心X/Y=±3 mm；外侧可用于落针，中心不再挖坑。
- 扣面下方四角提前收圆；12个对角射线点相对截面矩形包络最少内退2.55 mm，保留两侧内凹轮廓。
- 凸线宽0.6 mm、高约0.3 mm，交点上层约0.45 mm；与碗面融合，不做悬空细丝。
- 包络22×22×22.614 mm；顶部倒圆后的平边约2.51 mm。四坑附近20个测量点最薄留厚约3.28 mm，中央碗面基础留厚3.0 mm。

Blender 4.5.1 LTS验证为一个连通水密实体，边界边/非流形边均为0。独立毫米STL检查720502个三角面，每边恰由两面共享、方向一致，无退化面，体积约2581.07 mm³。尺寸射线验收公差0.02 mm；实际佩戴、防滑和耐压仍需试打。

左右主圆弧66个实际轮廓样本通过单向内收与同向曲率检查；比上一版中段每侧最多收进1.63 mm。另外两面的参考轴轮廓对比在0.02 mm验收公差内一致。

接合处采用统一截面，四角纵向轮廓做1.0 mm高斯几何平滑；孔口采用顺着实际端面法线的R0.4 mm圆弧。连接处14条轨迹1100个法线样本，步长不超过0.05 mm，最大方向变化4.28°；孔口窄带256条径向轨迹15616个样本，步长0.005 mm，最大方向变化5.00°。名义上限5°、数值容差0.01°。上半环51点法线壁厚检查最小1.60 mm。

## 构建与导出

`model.json`是唯一尺寸、坐标与公差源，单位cm。项目op通过通用引擎调度，运行时重新加载，场景具名对象在节点之间交接。

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
  --python-exit-code 1 --python projects/lotus_thimble/run_model.py
```

入口会清空执行实例的场景；在独立实例运行，保留其他未保存作品。需要Blender4.5或更新版本的MANIFOLD求解器。
产物写入gitignore的`output/`：

- `button_thimble_17x15p5mm_w14mm.blend`：场景显示cm，内部为米。
- `button_thimble_17x15p5mm_w14mm.stl`：明确换算为毫米，保留佩戴坐标方向。

STL导出按实际float32坐标抵消严格重合、反向的成对三角面，避免CSG微小折面在单位换算后形成重复内面。本次无需抵消反向面；不合并近点、不补洞。其余拓扑由独立读取STL的脚本验收。

```sh
python3 projects/lotus_thimble/tools/check_stl.py \
  projects/lotus_thimble/output/button_thimble_17x15p5mm_w14mm.stl \
  --size-mm 22 22 22.6142857143 \
  --report projects/lotus_thimble/spec/stl_verification_report.json
```

## 文件与参数

- `spec/preview.html` / `button_proposal.html`：确认后的手写三视图。
- `spec/requirement.md`：当前需求、尺寸与验收边界。
- `spec/verification_report.json` / `stl_verification_report.json`：实际网格、射线及STL数据。
- `spec/junction_comparison_report.json`：孔口上方接合曲面修改前后的法线对比。
- `spec/bore_lip_comparison_report.json`：孔口窄边修正的历史法线对比。
- `spec/side_profile_comparison_report.json`：当前左右侧面内收前后对比，含另外两面的参考轮廓检查。
- `ops/button_body.py`：法线等距椭圆环、内收填充支撑、适配曲面端面的孔口圆角、圆唇与凹碗。
- `ops/geometry.py`：项目几何助手；`pits.py`逐个挖坑，`threads.py`融合闭合凸线。
- `ops/button_verify.py`：双轴孔径、法线壁厚、端面圆角、内收轮廓、上半环壁厚、连接处法线连续性、左右侧面同向曲率、支撑四角收圆、四坑留厚/可用区与凸线高度。
- `ops/export_mm.py` / `tools/check_stl.py`：毫米导出与独立文件验收。

改`BORE_X`/`BORE_Z`调整指孔，改`WALL`/`BAND_W`调整环身。`PAD_SCALE`驱动原莲蓬顶部比例；内收曲线控制点、四眼位置和缝线端点也在JSON中。大幅改变比例需同步重审三视图和连接曲线。

## 首件试打

可将Y孔轴转为打印Z轴，整件落床后评估局部支撑、接触面及brim。顶部沿Y每端伸出4 mm，不要只把环端贴床而让扣面穿入平台。支撑尽量避开指孔、碗面、四眼和凸线。
先清理毛刺、试戴，再拿实际针尾由轻力检查四坑是否可落位。尚未切片或实物试验。
