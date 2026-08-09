# Script Index

> 新增/修改脚本后必须同步本表。按路径排序。这是本库的累积索引——不同步等于没沉淀。

| 路径 | 用途 | 可调参数 | 输出 | 幂等 | 备注 |
|---|---|---|---|---|---|
| primitives/make_box.py | 创建命名长方体（先删同名对象） | `NAME`, `SIZE`, `DIMENSIONS`, `LOCATION` | `OK created <NAME> dimensions=... at ...` | 是 | 尺寸非正方体即长方体 |
| objects/make_basket.py | 蜂巢镂空筐（六边形尖顶孔、孔整体内缩留实体角柱、奇数行对称、长边凹沿、两侧胶囊把手） | `LENGTH`,`WIDTH`,`HEIGHT`,`WALL`,`HEX_W`,`HEX_GAP`,`MARGIN_*`,`BOTTOM_MARGIN`,`SCALLOP_*`,`SCALLOP_OVER`,`HANDLE_*`,`BEVEL` | `OK created Basket outer=... hex_holes=... scallop=... handles=...` | 是 | 放纸样；墙3mm；孔不咬边、四角留实体柱；凹沿切割器抬出墙顶(SCALLOP_OVER)防共面残边；均bmesh流形 |
| objects/make_clip_tester.py | C夹+抱柱松紧度试印件（各带底座+3mm模拟墙片，独立两件） | `CLIP_H`,`JOINT_OD`,`JOINT_ID`,`PIN_OD`,`PIN_OD_BOT`,`PIN_BOT_H`,`SLOT_W`,`WALL_T`,`WALL_EXT`,`BASE_*`,`GAP_X`,`CYL_SEG` | `OK clip_tester: ClipTester(...) PinTester(...)` | 是 | 整筐分割前先打这套试配合；孔φ5.12/柱身φ5.0/柱底φ5.12；孔轴=Z便于平放打印 |
| scene/list_objects.py | 列出场景所有 mesh 对象及尺寸/位置 | （无） | `SCENE_OBJECTS: [(name, dims, loc), ...]` | 是 | 只读，用于验证 |
| scene/inspect_object.py | 打印对象网格统计（尺寸/顶点/面数/位置） | `NAME` | `INSPECT <NAME>: type=... dims=... verts=... polys=...` | 是 | 只读；面数高=布尔镂空生效 |
| scene/orbit_view.py | 设置 3D 视口到方位角/俯仰角/距离视角（便于截图） | `AZIMUTH`,`ELEVATION`,`DISTANCE`,`TARGET`,`PERSP`,`ZOOM` | `OK view set az=... el=... dist=... target=...` | 是 | 只改视口不增删对象；ZOOM>0且正交时按view_distance拉近看小件；配合 get_viewport_screenshot |
| scene/isolate_object.py | 只显示指定对象、隐藏其余mesh（聚焦截图） | `SHOW`（名字列表，空/None=全显恢复） | `OK isolate: shown=... hidden=...` | 是 | 只改hide_viewport可见性，不增删对象 |

<!-- 新脚本在此行上方插入 -->
