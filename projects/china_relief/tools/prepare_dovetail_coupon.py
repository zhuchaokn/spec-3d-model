"""Crop the real base mating outlines into a separate gray fit coupon."""
import json,zipfile
import numpy as np
from shapely.geometry import box
from shapely.affinity import translate
import prepare_print as p


def main():
    config=json.loads((p.ROOT/'model.json').read_text());c=config['constants'];pr=config['printing']
    r=json.loads((p.ROOT/'spec/data_report.json').read_text())
    x0,y0,x1,y1=r['tray_bounds_cm'];xs=np.linspace(x0,x1,3);ys=np.linspace(y0,y1,3)
    cx=xs[1];cy=ys[0]+(ys[1]-ys[0])/3
    half=pr['dovetail_test_half_width_mm']/10;h=pr['dovetail_test_height_mm']/20
    crop=box(cx-half,cy-h,cx+half,cy+h);items=[];records=[]
    for ix,name in [(0,'燕尾小样_公'),(1,'燕尾小样_母')]:
        cell=box(xs[ix],ys[0],xs[ix+1],ys[1])
        geom=p.prepare.tray_polygon(cell,ix,0,2,2,c).intersection(crop)
        geom=translate(geom,-(geom.bounds[0]+geom.bounds[2])/2,-cy)
        mesh=p.prism(geom,0,pr['dovetail_test_thickness_mm']/10);mesh.vertices*=10
        assert mesh.is_watertight and mesh.body_count==1
        mesh.export(p.ROOT/'output'/(pr['dovetail_test_filename'].removesuffix('.3mf')+'_'+name+'.stl'))
        items.append((name,[(name,pr['base_filament_id'],mesh)]))
        records.append({'name':name,'dimensions_mm':mesh.extents.tolist(),'watertight':True})
    bins=p.pack(items,config);assert len(bins)==1
    with zipfile.ZipFile(p.ROOT/'output'/pr['dovetail_project_filename']) as z:settings=json.loads(z.read('Metadata/project_settings.config'))
    settings['layer_height']=str(pr['base_layer_height_mm']);settings['xy_contour_compensation']='0'
    settings['print_settings_id']=f"{pr['base_layer_height_mm']:.2f}mm Standard @BBL P2S"
    target=p.ROOT/'output'/pr['dovetail_test_filename']
    p.write_project(target,bins[0]['items'],[v['id'] for v in pr['colors']],settings)
    p.prepare.write_json(p.ROOT/'spec/dovetail_coupon_report.json',{'source':'actual Tray_X1_Y1 / Tray_X2_Y1 outlines','profile_clearance_mm':c['TRAY_TAB_CLEARANCE']*10,'seam_gap_mm':c['TRAY_SEAM_GAP']*10,'parts':records,'separate_from_production_plates':True})
    print('Saved actual dovetail fit coupon:',target)

if __name__=='__main__':main()
