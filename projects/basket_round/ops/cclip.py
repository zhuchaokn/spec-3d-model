"""op: cclip — 建一个独立的 C 夹(卡合件)。

C夹 = 竖直圆墩(外径 od)− 中心竖孔(id)− 一道 slot_w 宽矩形(朝 open 方向开口)= C 形。
ctx.center: 墩质心(绝对)。ctx.params: od, id, slot_w, h, open('+x'/'-x'/'+y'/'-y')。
产出独立具名对象,直接摆在与筐半重叠的位置即可,**不 union**(合体难拆、易生非流形)。
"""
import s3d


def run(ctx):
    p = ctx.params
    od, idia, slot_w, h = p["od"], p["id"], p["slot_w"], p["h"]
    open_dir = p.get("open", "-x")
    cx, cy, cz = ctx.center
    post = f"_{ctx.name}_post"
    hole = f"_{ctx.name}_hole"
    slot = f"_{ctx.name}_slot"
    s3d.clean_by_names(names=(post, hole, slot, ctx.name))

    o = s3d.add_cylinder(ctx.name, od, h, ctx.center, seg=int(p.get("seg", 64)))
    # 中心竖孔
    bore = s3d.add_cylinder(hole, idia, h + 1.0, ctx.center)
    s3d.bool_diff(o, bore)
    # 开口槽:一个 slot_w 宽矩形,从孔通到墩外,朝 open 方向
    r = od / 2
    if open_dir in ("+x", "-x"):
        sgn = 1 if open_dir == "+x" else -1
        loc = (cx + sgn * r / 2, cy, cz)
        size = (od, slot_w, h + 1.0)
    else:
        sgn = 1 if open_dir == "+y" else -1
        loc = (cx, cy + sgn * r / 2, cz)
        size = (slot_w, od, h + 1.0)
    sl = s3d.add_box(slot, size, loc)
    s3d.bool_diff(o, sl)
    print(f"  [cclip] {ctx.name} od={od} id={idia} open={open_dir} "
          f"center={tuple(round(c,3) for c in ctx.center)}")
