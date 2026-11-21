"""Replace only the four tray geometries in a user-arranged 9-plate 3MF.

Preserve every build transform, plate assignment, province/test mesh and preset.
Discard previews and slicing caches, since they describe the old geometries.
No browser, screenshots or printer communication.
"""
import argparse,copy,json,re,uuid,zipfile,xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
import prepare_print as pp
ROOT=Path(__file__).resolve().parents[1]
C='{'+pp.CORE+'}';P='{'+pp.PROD+'}'
IDENTITY='1 0 0 0 1 0 0 0 1 0 0 0'
MATRIX='1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1'


def metadata(e):return {m.get('key'):m.get('value') for m in e.findall('metadata') if m.get('key')}


def setmeta(e,k,v):
    m=e.find(f"metadata[@key='{k}']")
    if m is None:m=ET.SubElement(e,'metadata',key=k)
    m.set('value',str(v))


def main():
    a=argparse.ArgumentParser();a.add_argument('source',type=Path);a.add_argument('destination',type=Path);args=a.parse_args()
    config=json.loads((ROOT/'model.json').read_text());manifest=json.loads((pp.OUT/'print_manifest.json').read_text())
    with zipfile.ZipFile(args.source) as archive:
        contents={n:archive.read(n) for n in archive.namelist()}
    core=ET.fromstring(contents['3D/3dmodel.model']);cfg=ET.fromstring(contents['Metadata/model_settings.config'])
    assert len(cfg.findall('plate'))==9
    objects={o.get('id'):o for o in core.findall(C+'resources/'+C+'object')}
    modified={};changed=[]
    next_id=max(int(o.get('id')) for path,content in contents.items() if path.endswith('.model')
                for o in ET.fromstring(content).findall(C+'resources/'+C+'object'))
    for oc in cfg.findall('object'):
        name=metadata(oc).get('name')
        if name not in manifest['multicolor_bases']:continue
        node=next(n for n in config['nodes'] if n['name']==name)
        data=json.loads((ROOT/'spec/data_report.json').read_text())
        # Color meshes share the aggregate tile XY centre and Z=0 origin.
        offset=np.array(node['offset'])*10;offset[2]=0
        parts={p['name']:p for p in manifest['multicolor_bases'][name]['parts']}
        components=objects[oc.get('id')].findall(C+'components/'+C+'component')
        byid={p.get('id'):p for p in oc.findall('part')}
        existing={metadata(p)['name'] for p in oc.findall('part')}
        for partname in parts.keys()-existing:
            next_id+=1
            path=components[0].get(P+'path').lstrip('/')
            if path not in modified:modified[path]=ET.fromstring(contents[path])
            ET.SubElement(modified[path].find(C+'resources'),C+'object',id=str(next_id),type='model',attrib={P+'UUID':str(uuid.uuid4())})
            comp=ET.SubElement(objects[oc.get('id')].find(C+'components'),C+'component',objectid=str(next_id),transform=IDENTITY,attrib={P+'path':'/'+path,P+'UUID':str(uuid.uuid4())})
            pc=copy.deepcopy(oc.findall('part')[0]);pc.set('id',str(next_id));setmeta(pc,'name',partname);oc.append(pc)
            byid[str(next_id)]=pc;components.append(comp)
        assert len(components)==len(parts)
        count=0
        for comp in components:
            pc=byid[comp.get('objectid')];partname=metadata(pc)['name'];part=parts[partname]
            arrays=np.load(pp.OUT/(partname+'.npz'));v=arrays['vertices'];f=arrays['faces']
            assert np.allclose(arrays['assembly_offset_mm'],offset,atol=1e-7)
            path=comp.get(P+'path').lstrip('/')
            if path not in modified:modified[path]=ET.fromstring(contents[path])
            obj=modified[path].find(f"{C}resources/{C}object[@id='{comp.get('objectid')}']")
            old=obj.find(C+'mesh')
            if old is not None:obj.remove(old)
            mesh=ET.SubElement(obj,C+'mesh');vs=ET.SubElement(mesh,C+'vertices');fs=ET.SubElement(mesh,C+'triangles')
            for x,y,z in v:ET.SubElement(vs,C+'vertex',x=f'{x:.9f}',y=f'{y:.9f}',z=f'{z:.9f}')
            for i,j,k in f:ET.SubElement(fs,C+'triangle',v1=str(i),v2=str(j),v3=str(k))
            comp.set('transform',IDENTITY)
            setmeta(pc,'matrix',MATRIX)
            for axis in 'xyz':setmeta(pc,'source_offset_'+axis,0)
            setmeta(pc,'extruder',part['color'])
            stat=pc.find('mesh_stat');stat.set('face_count',str(len(f)))
            count+=len(f)
        for m in oc.findall('metadata'):
            if 'face_count' in m.attrib:m.set('face_count',str(count))
        changed.append(name)
    assert len(changed)==4
    contents['3D/3dmodel.model']=ET.tostring(core,encoding='utf-8',xml_declaration=True)
    contents['Metadata/model_settings.config']=ET.tostring(cfg,encoding='utf-8',xml_declaration=True)
    for path,model in modified.items():contents[path]=ET.tostring(model,encoding='utf-8',xml_declaration=True)
    # Remove stale references as well as stale files.
    for m in core.findall(C+'metadata'):
        if m.get('name','').startswith('Thumbnail'):core.remove(m)
    contents['3D/3dmodel.model']=ET.tostring(core,encoding='utf-8',xml_declaration=True)
    removed=[]
    for path in list(contents):
        if path.startswith('Metadata/') and (path.endswith(('.png','.gcode','.md5')) or path in ['Metadata/slice_info.config','Metadata/filament_sequence.json']):
            removed.append(path);del contents[path]
    for path in ['[Content_Types].xml','_rels/.rels','3D/_rels/3dmodel.model.rels']:
        if path not in contents:continue
        # Bambu's OPC reader expects the original default namespace here.
        # Retain original serialization rather than introducing ns0 prefixes.
        def strip(match):
            entry=match.group(0)
            return b'' if re.search(rb'(?:Target|PartName)="[^"]+\.(?:png|gcode|md5)"',entry) else entry
        contents[path]=re.sub(rb'<(?:Relationship|Override)\b[^>]*?/>',strip,contents[path])
    with zipfile.ZipFile(args.destination,'w',zipfile.ZIP_DEFLATED) as archive:
        for path,content in contents.items():archive.writestr(path,content)
    print('Updated four bases, preserved 9 plates:',args.destination)

if __name__=='__main__':main()
