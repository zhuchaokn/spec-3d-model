"""Match source and sliced objects by name; Bambu CLI renumbers resource IDs."""
import argparse,json,zipfile,xml.etree.ElementTree as ET
import numpy as np
from scipy.spatial import cKDTree
import prepare_print as p
from revise_nine_plate_project import C,P,metadata
from verify_dovetail_assemblies import transformed


def read(path):
    with zipfile.ZipFile(path) as z:
        models={n:ET.fromstring(z.read(n)) for n in z.namelist() if n.endswith('.model')}
        cfg=ET.fromstring(z.read('Metadata/model_settings.config'))
    lookup={(path,o.get('id')):o for path,m in models.items() for o in m.findall(C+'resources/'+C+'object')}
    def geometry(path,oid):
        o=lookup[path,oid];mesh=o.find(C+'mesh')
        if mesh is not None:
            v=np.array([[float(a.get(k)) for k in ['x','y','z']] for a in mesh.findall(C+'vertices/'+C+'vertex')])
            return v,len(mesh.findall(C+'triangles/'+C+'triangle'))
        vertices=[];faces=0
        for comp in o.findall(C+'components/'+C+'component'):
            v,f=geometry(comp.get(P+'path',path).lstrip('/'),comp.get('objectid'));vertices.append(transformed(v,comp.get('transform')));faces+=f
        return np.vstack(vertices),faces
    build={i.get('objectid'):i for i in models['3D/3dmodel.model'].findall(C+'build/'+C+'item')}
    result={};ids={o.get('id'):metadata(o)['name'] for o in cfg.findall('object')}
    for o in cfg.findall('object'):
        m=metadata(o);v,f=geometry('3D/3dmodel.model',o.get('id'))
        colors={metadata(part)['name']:int(metadata(part).get('extruder',m['extruder'])) for part in o.findall('part')}
        result[m['name']]={'vertices':transformed(v,build[o.get('id')].get('transform')),'faces':f,'colors':colors,'settings':m}
    plates=[[ids[metadata(mi)['object_id']] for mi in plate.findall('model_instance')] for plate in cfg.findall('plate')]
    return result,plates


def main():
    ap=argparse.ArgumentParser();ap.add_argument('source');ap.add_argument('sliced');args=ap.parse_args()
    a,pa=read(args.source);b,pb=read(args.sliced);assert set(a)==set(b) and pa==pb
    records=[]
    for name,x in a.items():
        y=b[name];assert x['colors']==y['colors'] and x['faces']==y['faces']
        assert all(y['settings'].get(k)==v for k,v in x['settings'].items())
        error=max(float(cKDTree(x['vertices']).query(y['vertices'])[0].max()),float(cKDTree(y['vertices']).query(x['vertices'])[0].max()))
        assert error<.001,(name,error)
        records.append({'name':name,'global_position_error_mm':error,'triangle_count':x['faces'],'colors_and_settings_preserved':True})
    p.prepare.write_json(p.ROOT/'spec/slice_preservation_report.json',{'object_count':len(records),'plate_count':len(pa),'objects':records,'resource_ids_may_be_renumbered':True})
    print('Verified sliced 3MF keeps all object geometry, positions, colors, settings and nine-plate assignment')

if __name__=='__main__':main()
