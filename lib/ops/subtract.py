"""op: subtract — 建一个临时切割体,从 target 上布尔减掉。

ctx.params: size=(x,y,z) cm(切割体尺寸),shape=可选(默认 box)。
ctx.center: 切割体质心。ctx.targets: 被减对象(通常一个)。
产出:修改 target(不新增成品对象);临时切割体用后删除。
"""
import s3d


def run(ctx):
    size = ctx.params["size"]
    tmp_name = f"_cut_{ctx.name}"
    s3d.clean_by_names(names=(tmp_name,))
    cutter = s3d.add_box(tmp_name, size, ctx.center)
    for dep in ctx.targets.values():
        target = dep["object"]
        if target is None:
            raise ValueError(f"subtract {ctx.name}: target 对象不存在")
        s3d.bool_diff(target, cutter, apply=True, remove_cutter=False)
    # 减完删临时体
    s3d.clean_by_names(names=(tmp_name,))
    tnames = list(ctx.targets.keys())
    print(f"  [subtract] {ctx.name} -{size} from {tnames}")
