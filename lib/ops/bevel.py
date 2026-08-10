"""op: bevel — 对 target 选【水平边】做圆角(顶沿/底边圆润)。

只倒"两端点 Z 都≈z_plane 的水平边"(即底面/顶面轮廓边),不碰 z 带里的斜边
(如六边形孔侧壁)——否则会把孔沿也倒圆、顶点数爆炸。
ctx.targets: 被倒圆对象。ctx.params:
  radius(圆角半径 cm), segments(段数,默认20),
  z_plane(目标水平面绝对 Z,cm), z_tol(容差,默认0.05:两端点 |z-z_plane| 都<tol 才选),
  exclude_x0(可选,|x| 阈值:两端点都在此内的边跳过 → 保护接缝边不倒)。
"""
import s3d


def run(ctx):
    p = ctx.params
    radius = p["radius"]
    seg = int(p.get("segments", 20))
    z_plane = p["z_plane"]
    z_tol = p.get("z_tol", 0.05)
    ex0 = p.get("exclude_x0")   # None 或 |x| 阈值

    def filt(a, b):
        # 只选水平边:两端点 z 都贴近目标平面(排除孔侧壁等斜边)
        if abs(a[2] - z_plane) > z_tol or abs(b[2] - z_plane) > z_tol:
            return False
        if ex0 is not None and abs(a[0]) < ex0 and abs(b[0]) < ex0:
            return False   # 接缝边(x≈0)不倒,保平直好对合
        return True

    tnames = []
    for dep in ctx.targets.values():
        obj = dep["object"]
        if obj is None:
            raise ValueError(f"bevel {ctx.name}: target 不存在")
        s3d.bevel_edges(obj.name, radius, segments=seg, edge_filter=filt)
        tnames.append(obj.name)
    print(f"  [bevel] {ctx.name} r={radius} z_plane={z_plane} on {tnames}")
