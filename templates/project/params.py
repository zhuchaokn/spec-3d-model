"""params.py — 本项目的单一尺寸源。

所有尺寸/公差常量集中在此,单位 **cm**(除非注明)。组件 build.py 与
spec/preview.html 都镜像这些值——改数值只改这里一处。
"""

# ---- 外形 ----
# LENGTH = 0.0   # X, cm
# WIDTH  = 0.0   # Y, cm
# HEIGHT = 0.0   # Z, cm
# WALL   = 0.3   # 壁厚, cm

# ---- 打印约束 ----
# PRINT_VOL = (256, 256, 256)   # 打印体积 mm(如 Bambu P2S)

# ---- 公差(经验值) ----
# JOINT_ID  = 0.512   # 基准孔 φ5.12mm
# PIN_OD    = 0.50    # 柱身 φ5.0mm(滑配)
# PIN_OD_BOT= 0.512   # 柱底 φ5.12mm(过盈防脱)
