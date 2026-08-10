"""op: rounded_box — 在 ctx.center 建圆角矩形棱柱(竖直边可分别倒圆)。

ctx.params: size=(L,W,H) cm;radii=[r0,r1,r2,r3] 四竖边圆角半径,顺序=XY 四角
  [(-x,-y),(+x,-y),(+x,+y),(-x,+y)],某项=0 即该角直角。可选 seg。
用于筐体外壳:远端两角给圆角、缝端两角给 0。
"""
import s3d


def run(ctx):
    p = ctx.params
    size = p["size"]
    radii = p.get("radii", [0, 0, 0, 0])
    s3d.clean_by_names(names=(ctx.name,))
    obj = s3d.add_rounded_prism(ctx.name, size, ctx.center,
                                radii_cm=tuple(radii), seg=int(p.get("seg", 10)))
    print(f"  [rounded_box] {ctx.name} size={size} radii={radii} "
          f"center={tuple(round(c,3) for c in ctx.center)}")
    return obj
