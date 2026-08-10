"""op: rounded_subtract — 建圆角矩形棱柱切割器,从 target 布尔减掉(挖圆角腔)。

ctx.params: size=(L,W,H),radii=[r0,r1,r2,r3](同 rounded_box)。
ctx.center: 切割体质心。ctx.targets: 被减对象。
用于挖内腔:内腔远端两角圆(=外壳 R−WALL),缝端直角,壁厚恒定。切割器须探出被切面。
"""
import s3d


def run(ctx):
    p = ctx.params
    size = p["size"]
    radii = p.get("radii", [0, 0, 0, 0])
    tmp = f"_cut_{ctx.name}"
    s3d.clean_by_names(names=(tmp,))
    cutter = s3d.add_rounded_prism(tmp, size, ctx.center,
                                   radii_cm=tuple(radii), seg=int(p.get("seg", 10)))
    tnames = []
    for dep in ctx.targets.values():
        if dep["object"] is None:
            raise ValueError(f"rounded_subtract {ctx.name}: target 不存在")
        s3d.bool_diff(dep["object"], cutter, apply=True, remove_cutter=False)
        tnames.append(dep["object"].name)
    s3d.clean_by_names(names=(tmp,))
    print(f"  [rounded_subtract] {ctx.name} -{size} radii={radii} from {tnames}")
