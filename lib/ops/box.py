"""op: box — 在 ctx.center 建一个具名长方体(实体)。

ctx.params: size=(x,y,z) cm。定位 = ctx.center(质心)。
产出:名为 ctx.name 的 box。幂等由引擎/清理负责(此处直接建)。
"""
import s3d


def run(ctx):
    size = ctx.params["size"]
    s3d.clean_by_names(names=(ctx.name,))
    obj = s3d.add_box(ctx.name, size, ctx.center)
    print(f"  [box] {ctx.name} size={size} center={tuple(round(c,3) for c in ctx.center)}")
    return obj
