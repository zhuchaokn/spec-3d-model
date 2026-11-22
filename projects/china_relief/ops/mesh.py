"""Load a prepared, validated closed mesh. Dimensions live in model.json."""
import os
import numpy as np
import bpy
import s3d


def run(ctx):
    path=os.path.join(ctx.proj_dir,ctx.params['mesh_file'])
    with np.load(path,allow_pickle=False) as data:
        vertices=data['vertices']*s3d.CM
        faces=data['faces']
    mesh=bpy.data.meshes.new(ctx.name+'_mesh')
    mesh.from_pydata(vertices.tolist(),[],faces.tolist())
    mesh.update()
    obj=bpy.data.objects.new(ctx.name,mesh)
    group=ctx.params['group']
    if group=='terrain':
        collection_name=f'{ctx.params["code"]} {ctx.params["province"]}'
    elif group=='tray':
        collection_name='定位托盘'
    elif group=='terrain_assembly':
        collection_name=ctx.params['assembly_name']
    else:
        collection_name='试配件（先打印）'
    collection=bpy.data.collections.get(collection_name)
    if collection is None:
        collection=bpy.data.collections.new(collection_name)
    if collection.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(collection)
    collection.objects.link(obj)
    obj.location=tuple(v*s3d.CM for v in ctx.center)
    obj['group']=group
    obj['prepared_mesh']=path
    obj['tile']=ctx.params.get('tile',[])
    if group=='terrain':
        obj['province']=ctx.params['province']
        obj['code']=ctx.params['code']
    # Workbench object colors help distinguish province pieces; no render is used.
    import colorsys
    if group=='terrain':
        hue=((ctx.params['code']//10000)*.61803398875)%1
        obj.color=(*colorsys.hsv_to_rgb(hue,.35,.8),1)
    else:
        obj.color=(.24,.27,.3,1)
