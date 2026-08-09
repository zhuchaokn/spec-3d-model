"""op: capsule_cut — 对 target 减一个胶囊(把手镂空)。

ctx.center: 胶囊质心(绝对)。ctx.params: w, h, depth, axis('x'/'y'/'z')。
胶囊 = 中间矩形 + 两端半圆,沿 axis 法向拉伸 depth 穿透墙。
"""
import s3d


def run(ctx):
    p = ctx.params
    axis = p.get("axis", "x")
    tmp = f"_cut_{ctx.name}"
    s3d.clean_by_names(names=(tmp,))
    cutter = s3d.capsule(tmp, p["w"], p["h"], p["depth"], ctx.center, axis=axis)
    tnames = []
    for dep in ctx.targets.values():
        if dep["object"] is None:
            raise ValueError(f"capsule_cut {ctx.name}: target 不存在")
        s3d.bool_diff(dep["object"], cutter, apply=True, remove_cutter=False)
        tnames.append(dep["object"].name)
    s3d.clean_by_names(names=(tmp,))
    print(f"  [capsule_cut] {ctx.name} {p['w']}x{p['h']} axis={axis} from {tnames}")
