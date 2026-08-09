"""op: mirror — 把 source 对象跨 X=0 平面镜像成一个新具名对象。

用于"建好一半的壳,镜像出另一半"。跨世界 X=0 镜像:新对象 location.x 取反,
mesh 沿局部 X 翻转,并翻转法线保持朝外(负缩放会反绕)。
ctx.params: source(要镜像的对象名),axis(默认 'x')。ctx.center/target 不用。
"""
import bmesh
import bpy
import mathutils
import s3d


def run(ctx):
    src_name = ctx.params["source"]
    src = bpy.data.objects.get(src_name)
    if src is None:
        raise ValueError(f"mirror {ctx.name}: source {src_name} 不存在")
    s3d.clean_by_names(names=(ctx.name,))
    dup = s3d.copy_object(src, ctx.name)
    # 跨世界 X=0:location.x 取反 + mesh 局部 X 翻转
    dup.location = (-src.location.x, src.location.y, src.location.z)
    dup.data.transform(mathutils.Matrix.Scale(-1.0, 4, (1.0, 0.0, 0.0)))
    # 负缩放反绕 → 翻转法线朝外
    bm = bmesh.new()
    bm.from_mesh(dup.data)
    for f in bm.faces:
        f.normal_flip()
    bm.to_mesh(dup.data)
    bm.free()
    dup.data.update()
    print(f"  [mirror] {ctx.name} = mirror({src_name}) across X=0")
    return dup
