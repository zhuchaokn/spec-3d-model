"""isolate_object.py — 只显示指定对象，隐藏其余 mesh（便于聚焦截图）。

用途：场景里有多个对象互相遮挡时，隔离出要看的那个再截图。
是否幂等：是（只改视口可见性 hide_viewport，不增删对象）。
SHOW=[] 或 None 时恢复全部可见（取消隔离）。
可调参数见下方常量，改完用 execute_blender_code(file_path=__file__) 跑。
输出：最后一行 print 结果。
"""
import bpy

# ---- params (edit me) ----
SHOW = []  # 只显示这些；空/None=全显（恢复全部）
# --------------------------


def main():
    shown, hidden = [], []
    show_set = set(SHOW) if SHOW else None
    for obj in bpy.data.objects:
        if obj.type != 'MESH':
            continue
        if show_set is None:
            obj.hide_viewport = False
            shown.append(obj.name)
        elif obj.name in show_set:
            obj.hide_viewport = False
            shown.append(obj.name)
        else:
            obj.hide_viewport = True
            hidden.append(obj.name)
    print(f"OK isolate: shown={shown} hidden={hidden}")


main()
