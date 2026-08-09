"""op: frustum — 在 ctx.center 建竖直圆台(实体),可选 union 进 target。

ctx.params: d_bot, d_top, h (cm)。轴=Z。底大顶小的 Pin 用它。
若有 target:建好后 union 进 target(卡合件长在筐半上);否则留作独立对象。
"""
import s3d


def run(ctx):
    p = ctx.params
    s3d.clean_by_names(names=(ctx.name,))
    obj = s3d.add_frustum(ctx.name, p["d_bot"], p["d_top"], p["h"], ctx.center,
                          seg=int(p.get("seg", 64)))
    tgt = [d["object"] for d in ctx.targets.values() if d["object"]]
    if tgt:
        s3d.bool_union(tgt[0], obj)    # 真布尔并:去掉重叠内壁,保持水密
        print(f"  [frustum] {ctx.name} d_bot={p['d_bot']} d_top={p['d_top']} → union {tgt[0].name}")
    else:
        print(f"  [frustum] {ctx.name} d_bot={p['d_bot']} d_top={p['d_top']} center={tuple(round(c,3) for c in ctx.center)}")
