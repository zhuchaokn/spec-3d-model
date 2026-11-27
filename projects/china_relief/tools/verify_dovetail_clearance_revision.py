"""Verify changing female clearance affects only the eight socket margins."""
import argparse,json,zipfile,xml.etree.ElementTree as ET
import numpy as np
from shapely.geometry import box
from shapely.ops import unary_union
import prepare_print as p
from revise_nine_plate_project import C,P,metadata


def main():
    ap=argparse.ArgumentParser();ap.add_argument('old_registry');ap.add_argument('old_project');ap.add_argument('new_project');a=ap.parse_args()
    old=json.loads(open(a.old_registry).read());cfg=json.loads((p.ROOT/'model.json').read_text());c=cfg['constants'];before=old['constants']
    assert [k for k in c if c[k]!=before[k]]==['TRAY_TAB_CLEARANCE']
    assert c['TRAY_TAB_CLEARANCE']>0 and c['TRAY_TAB_CLEARANCE']!=before['TRAY_TAB_CLEARANCE']
    r=json.loads((p.ROOT/'spec/data_report.json').read_text());x0,y0,x1,y1=r['tray_bounds_cm'];xs=np.linspace(x0,x1,3);ys=np.linspace(y0,y1,3)
    width=c['TRAY_TAB_HEAD_WIDTH'];length=c['TRAY_TAB_LENGTH'];clear=max(c['TRAY_TAB_CLEARANCE'],before['TRAY_TAB_CLEARANCE']);changes=[]
    for iy in range(2):
        for ix in range(2):
            cell=box(xs[ix],ys[iy],xs[ix+1],ys[iy+1]);prior=p.prepare.tray_polygon(cell,ix,iy,2,2,before);new=p.prepare.tray_polygon(cell,ix,iy,2,2,c)
            windows=[]
            for fraction in [1/3,2/3]:
                y=ys[iy]+(ys[iy+1]-ys[iy])*fraction;x=xs[ix]+(xs[ix+1]-xs[ix])*fraction
                if ix:windows.append(box(xs[ix]-2*clear,y-width/2-2*clear,xs[ix]+length+2*clear,y+width/2+2*clear))
                if iy:windows.append(box(x-width/2-2*clear,ys[iy]-2*clear,x+width/2+2*clear,ys[iy]+length+2*clear))
            added=new.difference(prior);removed=prior.difference(new)
            assert added.union(removed).difference(unary_union(windows)).area<1e-10
            if c['TRAY_TAB_CLEARANCE']>before['TRAY_TAB_CLEARANCE']:assert added.area<1e-10
            else:assert removed.area<1e-10
            if ix==iy==0:assert added.area+removed.area<1e-10
            else:assert added.area+removed.area>0
            changes.append({'name':f'Tray_X{ix+1}_Y{iy+1}','added_socket_margin_mm2':added.area*100,'removed_socket_margin_mm2':removed.area*100,'all_changes_inside_female_socket_margins':True})
    unchanged=[]
    with zipfile.ZipFile(a.old_project) as oldz,zipfile.ZipFile(a.new_project) as newz:
        oc=ET.fromstring(oldz.read('3D/3dmodel.model'));nc=ET.fromstring(newz.read('3D/3dmodel.model'))
        assert ET.tostring(oc.find(C+'build'))==ET.tostring(nc.find(C+'build'))
        oldcfg=ET.fromstring(oldz.read('Metadata/model_settings.config'));newcfg=ET.fromstring(newz.read('Metadata/model_settings.config'))
        assert [ET.tostring(p) for p in oldcfg.findall('plate')]==[ET.tostring(p) for p in newcfg.findall('plate')]
        assert oldz.read('Metadata/project_settings.config')==newz.read('Metadata/project_settings.config')
        roots={o.get('id'):o for o in nc.findall(C+'resources/'+C+'object')}
        for obj in newcfg.findall('object'):
            name=metadata(obj)['name']
            if name.startswith('Tray_') and name!='Tray_X1_Y1':continue
            for comp in roots[obj.get('id')].findall(C+'components/'+C+'component'):
                path=comp.get(P+'path').lstrip('/');assert oldz.read(path)==newz.read(path)
            unchanged.append(name)
    assert len(unchanged)==30
    result={'before_clearance_mm':before['TRAY_TAB_CLEARANCE']*10,'after_clearance_mm':c['TRAY_TAB_CLEARANCE']*10,'male_geometry_unchanged':True,'straight_seam_gap_mm':c['TRAY_SEAM_GAP']*10,'unchanged_objects':unchanged,'unchanged_plate_assignment':True,'only_changed_production_plates':[3,4,5],'base_changes':changes}
    p.prepare.write_json(p.ROOT/'spec/dovetail_clearance_revision_report.json',result)
    print('Verified only female socket margins changed; 29 map pieces and male-only plate 2 are byte-identical')

if __name__=='__main__':main()
