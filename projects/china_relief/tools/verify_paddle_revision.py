"""Check circular-head dimensions, neck strength and localized base changes."""
import argparse,json,zipfile,xml.etree.ElementTree as ET
import numpy as np
from shapely.geometry import box,LineString
from shapely.ops import unary_union
import prepare_print as p
from revise_nine_plate_project import C,P,metadata


def main():
    ap=argparse.ArgumentParser();ap.add_argument('old_registry');ap.add_argument('old_project');ap.add_argument('new_project');args=ap.parse_args()
    old=json.loads(open(args.old_registry).read());cfg=json.loads((p.ROOT/'model.json').read_text());c=cfg['constants']
    assert c['TRAY_TAB_WIDTH']==old['constants']['TRAY_TAB_WIDTH'] and c['TRAY_TAB_HEAD_WIDTH']==old['constants']['TRAY_TAB_HEAD_WIDTH']
    assert c['TRAY_TAB_CLEARANCE']==old['constants']['TRAY_TAB_CLEARANCE'] and c['TRAY_SEAM_GAP']==old['constants']['TRAY_SEAM_GAP']
    profile=p.prepare.paddle_profile(c,True);head=c['TRAY_TAB_HEAD_WIDTH'];width=c['TRAY_TAB_WIDTH'];length=c['TRAY_TAB_LENGTH'];blend=c['TRAY_PADDLE_BLEND_RADIUS']
    center=length-head/2
    head_width=profile.intersection(LineString([(center,-head),(center,head)])).length
    neck_width=profile.intersection(LineString([(blend*1.5,-head),(blend*1.5,head)])).length
    assert np.isclose(head_width,head,atol=.0002) and np.isclose(neck_width,width,atol=1e-8)
    assert head_width-neck_width>2*c['TRAY_TAB_CLEARANCE']
    # Both sides of the circle approach the neck through small angle changes.
    coords=np.array(profile.exterior.coords);edges=np.diff(coords,axis=0)
    valid=np.linalg.norm(edges,axis=1)>1e-9
    angles=[]
    for i in range(len(edges)-1):
        if not (valid[i] and valid[i+1]) or coords[i+1,0]<=c['NUMERICAL_GAP']*2:continue
        a,b=edges[i],edges[i+1];angles.append(float(np.arccos(np.clip(np.dot(a,b)/np.linalg.norm(a)/np.linalg.norm(b),-1,1))))
    max_turn=max(angles);assert max_turn<np.deg2rad(5)
    report=json.loads((p.ROOT/'spec/data_report.json').read_text());x0,y0,x1,y1=report['tray_bounds_cm'];xs=np.linspace(x0,x1,3);ys=np.linspace(y0,y1,3);changes=[]
    for iy in range(2):
        for ix in range(2):
            cell=box(xs[ix],ys[iy],xs[ix+1],ys[iy+1]);before=p.prepare.tray_polygon(cell,ix,iy,2,2,old['constants']);after=p.prepare.tray_polygon(cell,ix,iy,2,2,c)
            margin=max(blend*2,c['TRAY_TAB_CLEARANCE']*2);windows=[]
            for f in [1/3,2/3]:
                x=xs[ix]+(xs[ix+1]-xs[ix])*f;y=ys[iy]+(ys[iy+1]-ys[iy])*f
                if ix<1:windows.append(box(xs[ix+1]-margin,y-head/2-margin,xs[ix+1]+length+margin,y+head/2+margin))
                if ix>0:windows.append(box(xs[ix]-margin,y-head/2-margin,xs[ix]+length+margin,y+head/2+margin))
                if iy<1:windows.append(box(x-head/2-margin,ys[iy+1]-margin,x+head/2+margin,ys[iy+1]+length+margin))
                if iy>0:windows.append(box(x-head/2-margin,ys[iy]-margin,x+head/2+margin,ys[iy]+length+margin))
            delta=before.symmetric_difference(after);assert delta.area>0 and delta.difference(unary_union(windows)).area<1e-8
            changes.append({'name':f'Tray_X{ix+1}_Y{iy+1}','only_interface_regions_changed':True,'changed_area_mm2':delta.area*100})
    preserved=[]
    with zipfile.ZipFile(args.old_project) as oldz,zipfile.ZipFile(args.new_project) as newz:
        a=ET.fromstring(oldz.read('3D/3dmodel.model'));b=ET.fromstring(newz.read('3D/3dmodel.model'));ac=ET.fromstring(oldz.read('Metadata/model_settings.config'));bc=ET.fromstring(newz.read('Metadata/model_settings.config'))
        assert ET.tostring(a.find(C+'build'))==ET.tostring(b.find(C+'build'))
        assert [ET.tostring(p) for p in ac.findall('plate')]==[ET.tostring(p) for p in bc.findall('plate')]
        assert oldz.read('Metadata/project_settings.config')==newz.read('Metadata/project_settings.config')
        roots={o.get('id'):o for o in b.findall(C+'resources/'+C+'object')}
        for obj in bc.findall('object'):
            name=metadata(obj)['name']
            if name.startswith('Tray_'):continue
            for comp in roots[obj.get('id')].findall(C+'components/'+C+'component'):
                path=comp.get(P+'path').lstrip('/');assert oldz.read(path)==newz.read(path)
            preserved.append(name)
    assert len(preserved)==29
    result={'style':'broad_neck_circular_head','nominal_head_diameter_mm':head*10,'measured_head_diameter_mm':head_width*10,'measured_neck_width_mm':neck_width*10,'projection_mm':length*10,'transition_radius_mm':blend*10,'max_exposed_segment_turn_deg':np.rad2deg(max_turn),'profile_clearance_mm':c['TRAY_TAB_CLEARANCE']*10,'only_interfaces_changed':changes,'preserved_map_objects':preserved,'requires_all_four_new_bases':True}
    p.prepare.write_json(p.ROOT/'spec/paddle_revision_report.json',result)
    print('Verified round Ø12 head / 8 mm neck, smooth joins, 29 preserved map pieces; all four bases changed')

if __name__=='__main__':main()
