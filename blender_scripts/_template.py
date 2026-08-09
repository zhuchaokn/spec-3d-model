"""<一句话用途>

是否幂等：是/否。
可调参数见下方常量，改完用 execute_blender_code(file_path=__file__) 跑。
输出：最后一行 print 结果。
"""
import bpy

# ---- params (edit me) ----
NAME = "Example"
# --------------------------

# 幂等：创建前先删同名对象
for obj in list(bpy.data.objects):
    if obj.name == NAME:
        bpy.data.objects.remove(obj, do_unlink=True)

# ... 你的 bpy 操作 ...

print(f"OK <发生了什么>")
