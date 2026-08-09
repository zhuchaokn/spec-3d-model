"""params.py — 筐子项目单一尺寸源。

单位 cm(除非注明)。值取自已验证的旧 make_basket.py。组件 build.py 与
spec/preview.html 都镜像这里——改数值只改这一处。
"""

# ---- 外形 ----
LENGTH = 29.0        # X 长边, cm
WIDTH = 20.0         # Y 短边, cm
HEIGHT = 20.0        # Z 高, cm
WALL = 0.3           # 壁厚 3mm

# ---- 六边形镂空(pointy-top,尖顶朝上,FDM 竖直打无水平桥) ----
HEX_W = 2.5          # 孔宽(平边到平边) cm,四面统一
HEX_GAP = 0.7        # 孔间墙网宽 cm
MARGIN_SIDE = 1.0    # 沿墙左右留边 cm
MARGIN_BOTTOM = 1.2  # 墙下沿留边 cm
MARGIN_TOP = 1.0     # 墙上沿留边 cm
BOTTOM_MARGIN = 1.0  # 底板四周留边 cm

# ---- 长边(前/后墙 ±Y)凹沿 \___/ ----
SCALLOP_DIP = 5.0    # 中间凹下深度 cm
SCALLOP_CORNER = 4.0 # 两端满高段长 cm
SCALLOP_FLAT = 6.0   # 中间平底半宽 cm
SCALLOP_OVER = 1.0   # 切割器顶部超出墙顶量 cm(防共面残边)

# ---- 短边(左/右墙 ±X)胶囊把手 ----
HANDLE_W = 8.0       # 把手宽(胶囊总长) cm
HANDLE_H = 4.0       # 把手高(胶囊高=2*半径) cm
HANDLE_GAP_TOP = 3.0 # 把手顶距墙顶 cm

BEVEL = 0.04         # 倒角 cm(0=不倒)

# ---- 拆分:沿 X=0 切左右两半(P2S 256³mm 打不下 29cm 最长边) ----
PRINT_VOL = (256, 256, 256)  # Bambu P2S 打印体积 mm
SPLIT = True
SPLIT_GAP = 0.015    # 切面让位 0.15mm
SEAM_HALF = 0.75     # 切缝禁孔带半宽 cm:此范围内不打孔,留实体接卡合

# ---- 卡合:C夹 + 圆台 Pin(前后墙各一套)。公差经验值,先打试配件定死 ----
# 俯视看 Pin/C夹都是圆。装配:Pin 底大顶小,**从下往上滑入** C夹竖孔,到底楔紧。
JOINT_OD = 0.90      # C夹墩外径 φ9mm(半径 0.45)
JOINT_ID = 0.512     # C夹内孔 φ5.12mm(滑动基准孔,竖直=Z)
JOINT_WALL = 0.20    # C夹环壁厚 2mm((OD-ID)/2≈0.194,取 0.2 与筐墙搭接)
# Pin 圆台(平滑楔入,非两段圆柱):
PIN_D_TOP = 0.50     # 圆台顶径 φ5.0mm(< 孔 → 入口微涩滑动)
PIN_D_BOT = 0.512    # 圆台底径 φ5.12mm(= 孔 → 到底过盈卡住防脱)
SLOT_W = 0.30        # C夹开口缝宽 = 墙厚 3mm(用 3mm 矩形 bool 减出朝外的口)
JOINT_TOP = 15.0     # 卡合柱顶高 cm(= 凹沿最低点,勿凸进凹口)

# 圆心定位(俯视):见 requirement.md「卡合定位」。核心量:
JOINT_R = JOINT_OD / 2            # C夹外半径 0.45
CCLIP_OFFSET = JOINT_R - 0.2     # C夹圆心相对缝端沿墙长(X)外移量 = 0.25cm
#   Pin 圆心 = 该半缝端、墙厚中心线上(缝面正中)。
#   C夹圆心 = 从缝端沿墙长再移出 CCLIP_OFFSET(先 -半径0.45 让环内壁贴缝,
#             再 +0.2 让 2mm 环壁与筐墙搭接)。前后墙各一套,共 Pin×2 / C夹×2。

SPLIT_SHOW_GAP = 4.0 # 展示时两半沿 X 分开间距 cm(仅查看用,导出前置 0)
CYL_SEG = 64         # 圆柱分段
