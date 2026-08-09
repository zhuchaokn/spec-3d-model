"""op: frustum — 在 ctx.center 建一个竖直圆台(独立实体)。

ctx.params: d_bot, d_top, h (cm),可选 seg。轴=Z。dia_top=0 即圆锥。
产出独立的具名对象。若要和别的件配合,一般直接摆在重叠位置即可,不 union
(合体难拆、且易生非流形/水密问题;详见 lib/ENGINE.md 常见坑)。
"""
import s3d


def run(ctx):
    p = ctx.params
    s3d.clean_by_names(names=(ctx.name,))
    s3d.add_frustum(ctx.name, p["d_bot"], p["d_top"], p["h"], ctx.center,
                    seg=int(p.get("seg", 64)))
    print(f"  [frustum] {ctx.name} d_bot={p['d_bot']} d_top={p['d_top']} h={p['h']} "
          f"center={tuple(round(c,3) for c in ctx.center)}")
