# 左手食指莲蓬顶针

按用户确认的手写三视图构建，打印件为一个水密、连通的实体。

## 文件

- `model.json`：唯一尺寸源，单位 cm；内径 1.5 cm。
- `spec/preview.html`：已确认三视图，镜像注册表中的尺寸。
- `spec/requirement.md`：设计要求与打印边界。
- `spec/verification_report.json`：对实际 Blender 网格进行的验证。
- `run_model.py`：引擎入口。
- `ops/body.py`：圆滑指环、填实肩部、圆唇和凹碗。
- `ops/pits.py`：逐个挖七个圆底盲坑。
- `ops/verify.py`：拓扑、包络、BVH 射线测量。
- `ops/export_mm.py`：将米坐标明确换成毫米导出二进制 STL。

## 构建

需要 Blender 4.5 或更新版本，闭合体并集、指孔切割和小坑采用 MANIFOLD 求解器，处理相切/重合面的连接。切孔后直接检查水密性，不再焊接布尔结果中的邻近顶点，避免尺寸调整时压坏窄面。库与引擎在每次运行时 reload。

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
  --python-exit-code 1 --python projects/lotus_thimble/run_model.py
```

也可使用 BlenderMCP 的 `execute_blender_code(file_path=.../run_model.py)`。
入口会清空**当前执行实例**的场景，随后按注册表拓扑构建；不要在有未保存作品的实例中运行。

产物写入 `output/`（gitignore）：

- `lotus_thimble_15mm.stl`：毫米坐标，保留佩戴坐标方向。
- `lotus_thimble_15mm.blend`：场景单位显示 cm，Blender 内部为米。

## 参数调整

调整手指尺寸只改 `BORE_D`。`RING_R` 与 `RIM_Z` 自动跟随，中央坑底留厚由 `CORE_THICKNESS=0.2` 控制，不会因内径增大而被动变薄。
本次内径由 12 mm 调整为 15 mm；环身外径随基础壁厚增至 19 mm，针托随指孔升高 1.5 mm。环宽、针托外径、碗口、小坑、圆唇及各种圆角均独立参数化。大幅修改时需要重审三视图，几何约束不满足时构建会报错。

当前实测包络 19×14×21.4 mm，内径 15 mm，中央留厚 2 mm，七坑深 0.8 mm；圆唇顶部平边约 1.59 mm。
数据报告包含实际射线命中、连通块数、边界边/非流形边与体积。

指环端面与填充肩部的连接沿用径向/Y 截面的 R0.6 mm 圆角，再平滑过渡到上部针托，避免并集重新盖出锐边。`LOFT_CORNER_MIN` 跟随 `OUTER_EDGE_R`，不再使用独立的 0.06 mm 小圆角。接合处两端、两侧共 112 个射线测量点的最大轮廓误差约 0.00093 mm；旧版模型在同一检查中因约 0.0804 mm 的凸出台阶被拒绝。
本版毫米 STL 为 139362 个三角面，每边恰由两面共享、方向一致，无退化三角形，体积约 1565.98 mm³。

## 首件试打

STL 未绑定切片配置。首次导入切片器时核对尺寸为 19×14×21.4 mm，材料与受力方向由实际使用确定。
孔轴原为 Y；可转成打印 Z 轴，指孔竖直以减少孔内支撑。针托沿该轴比环身多伸出 2 mm/端，不能直接将环端贴床而让圆唇穿入平台：需要整件落床并评估局部支撑、底部接触面积及 brim。
支撑接触尽量避开孔口、碗面和小坑；不要把数据水密等同于无需支撑。
建议先打这一枚小件，清理毛刺，用实际缝针轻力试配，再确认戴入、弯指舒适度、防滑及耐压。尚未完成切片或实物试打。
