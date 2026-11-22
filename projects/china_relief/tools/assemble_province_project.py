"""Replace small standalone provinces/test pieces with two multi-color objects."""
import argparse,json,re,uuid,zipfile,xml.etree.ElementTree as ET
import numpy as np,trimesh
import prepare_print as p
from revise_nine_plate_project import C,P,metadata,setmeta,IDENTITY,MATRIX


def main():
    parser=argparse.ArgumentParser();parser.add_argument('source');parser.add_argument('destination');args=parser.parse_args()
    config=json.loads((p.ROOT/'model.json').read_text());pr=config['printing'];manifest=json.loads((p.OUT/'print_manifest.json').read_text())
    with zipfile.ZipFile(args.source) as z:files={n:z.read(n) for n in z.namelist()}
    core=ET.fromstring(files['3D/3dmodel.model']);cfg=ET.fromstring(files['Metadata/model_settings.config']);res=core.find(C+'resources');build=core.find(C+'build');plates=cfg.findall('plate')
    removed={metadata(mi)['object_id'] for mi in plates[0].findall('model_instance')}
    codes={str(code) for group in pr['province_assemblies'] for code in group['codes']}
    for obj in cfg.findall('object'):
        if metadata(obj)['name'].split('_')[0] in codes:removed.add(obj.get('id'))
    assert len(removed)==7
    for obj in list(res):
        if obj.get('id') in removed:res.remove(obj)
    for item in list(build):
        if item.get('objectid') in removed:build.remove(item)
    for obj in cfg.findall('object'):
        if obj.get('id') in removed:cfg.remove(obj)
    for plate in plates:
        for mi in plate.findall('model_instance'):
            if metadata(mi)['object_id'] in removed:plate.remove(mi)
    assemble=cfg.find('assemble')
    for item in list(assemble):
        if item.get('object_id') in removed:assemble.remove(item)
    nextid=max(int(o.get('id')) for name,data in files.items() if name.endswith('.model') for o in ET.fromstring(data).findall(C+'resources/'+C+'object'))
    items=[]
    for group in pr['province_assemblies']:
        parts=[]
        for part in manifest['multicolor_assemblies'][group['name']]['parts']:
            a=np.load(p.OUT/(part['name']+'.npz'));mesh=trimesh.Trimesh(vertices=a['vertices'],faces=a['faces'],process=False)
            parts.append((part['name'],part['color'],mesh))
        items.append((group['name'],parts))
    bins=p.pack(items,config);assert len(bins)==1
    added=[]
    for index,item in enumerate(bins[0]['items']):
        path=f'3D/Objects/province_assembly_{index}.model'
        model=ET.Element(C+'model',unit='millimeter');resources=ET.SubElement(model,C+'resources');partids=[]
        for name,color,mesh in item['parts']:
            nextid+=1;oid=str(nextid);obj=ET.SubElement(resources,C+'object',id=oid,type='model',attrib={P+'UUID':str(uuid.uuid4())});m=ET.SubElement(obj,C+'mesh');vs=ET.SubElement(m,C+'vertices');fs=ET.SubElement(m,C+'triangles')
            for x,y,z in mesh.vertices:ET.SubElement(vs,C+'vertex',x=f'{x:.9f}',y=f'{y:.9f}',z=f'{z:.9f}')
            for a,b,c in mesh.faces:ET.SubElement(fs,C+'triangle',v1=str(a),v2=str(b),v3=str(c))
            partids.append((oid,name,color,len(mesh.faces)))
        nextid+=1;rootid=str(nextid);root=ET.SubElement(res,C+'object',id=rootid,type='model',attrib={P+'UUID':str(uuid.uuid4())});components=ET.SubElement(root,C+'components')
        oc=ET.SubElement(cfg,'object',id=rootid);setmeta(oc,'name',item['name']);setmeta(oc,'extruder',3)
        for key in p.OBJECT_LIGHTWEIGHT_KEYS:setmeta(oc,key,{'wall_loops':'2','sparse_infill_density':'5%','sparse_infill_pattern':'gyroid','top_shell_layers':'4','bottom_shell_layers':'3'}[key])
        setmeta(oc,'layer_height',pr['card_layer_height_mm']);setmeta(oc,'xy_contour_compensation',pr['xy_contour_compensation_mm'])
        for oid,name,color,count in partids:
            ET.SubElement(components,C+'component',objectid=oid,transform=IDENTITY,attrib={P+'path':'/'+path,P+'UUID':str(uuid.uuid4())})
            part=ET.SubElement(oc,'part',id=oid,subtype='normal_part');setmeta(part,'name',name);setmeta(part,'extruder',color);setmeta(part,'matrix',MATRIX)
            ET.SubElement(part,'mesh_stat',face_count=str(count),edges_fixed='0',degenerate_facets='0',facets_removed='0',facets_reversed='0',backwards_edges='0')
        rotation='0 1 0 -1 0 0 0 0 1' if item['rotate'] else '1 0 0 0 1 0 0 0 1';transform=f"{rotation} {item['x']} {item['y']} 0"
        ET.SubElement(build,C+'item',objectid=rootid,transform=transform,printable='1')
        mi=ET.SubElement(plates[0],'model_instance');setmeta(mi,'object_id',rootid);setmeta(mi,'instance_id',0);setmeta(mi,'identify_id',nextid+1000)
        ET.SubElement(assemble,'assemble_item',object_id=rootid,instance_id='0',transform=transform,offset='0 0 0')
        files[path]=ET.tostring(model,encoding='utf-8',xml_declaration=True);added.append(path)
    setmeta(plates[0],'plater_name','京津冀 / 江苏上海 · 整体多色')
    assert len(cfg.findall('object'))==len(build)==33 and len(plates)==9
    used={a.get(P+'path').lstrip('/') for a in core.findall(C+'resources/'+C+'object/'+C+'components/'+C+'component')}
    for path in list(files):
        if path.startswith('3D/Objects/') and path not in used:del files[path]
    relpath='3D/_rels/3dmodel.model.rels'
    def keep(match):
        target=re.search(rb'Target="([^"]+)"',match.group(0));return match.group(0) if target is None or target.group(1).decode().lstrip('/') in used else b''
    rel=re.sub(rb'<Relationship\b[^>]*?/>',keep,files[relpath])
    for i,path in enumerate(added):rel=rel.replace(b'</Relationships>',f'<Relationship Target="/{path}" Id="assembly-{i}" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>'.encode())
    files[relpath]=rel;files['3D/3dmodel.model']=ET.tostring(core,encoding='utf-8',xml_declaration=True);files['Metadata/model_settings.config']=ET.tostring(cfg,encoding='utf-8',xml_declaration=True)
    with zipfile.ZipFile(args.destination,'w',zipfile.ZIP_DEFLATED) as z:
        for path,data in files.items():z.writestr(path,data)
    print('Saved nine plates / 33 objects; no standalone Beijing, Tianjin, Shanghai or old Beijing sample:',args.destination)

if __name__=='__main__':main()
