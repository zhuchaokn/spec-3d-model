"""Rebuild only tray meshes from verified prepared XY and fixed terrain heights.
Rebuilds depth and national outline clearance without resampling province terrain.
A nominal outline snapshot prevents repeated outward buffering on reruns.
"""
import json,hashlib
from pathlib import Path
import numpy as np
from shapely.geometry import shape,box,mapping
from shapely.ops import unary_union
import prepare
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'data/processed'


def main():
    config=json.loads((ROOT/'model.json').read_text());c=config['constants'];report=json.loads((ROOT/'spec/data_report.json').read_text())
    x0,y0,x1,y1=report['tray_bounds_cm'];nx,ny=config['data']['required_tray_grid'];xs=np.linspace(x0,x1,nx+1);ys=np.linspace(y0,y1,ny+1)
    recess=shape(json.loads((OUT/'national_recess.geojson').read_text())['geometry']);fixed=shape(json.loads((OUT/'fixed_details.geojson').read_text())['features'][0]['geometry']);inset=shape(json.loads((OUT/'south_sea_inset.geojson').read_text())['geometry'])
    nominal_path=OUT/'national_recess_nominal.geojson'
    if not nominal_path.exists():nominal_path.write_text((OUT/'national_recess.geojson').read_text())
    nominal=shape(json.loads(nominal_path.read_text())['geometry'])
    recess=nominal.buffer(c['SLOT_CLEARANCE'],quad_segs=24,join_style='round')
    inner=box(x0+c['TRAY_FRAME_WIDTH'],y0+c['TRAY_FRAME_WIDTH'],x1-c['TRAY_FRAME_WIDTH'],y1-c['TRAY_FRAME_WIDTH']).buffer(c['NUMERICAL_GAP'],join_style=2);frame=box(x0,y0,x1,y1).difference(inner).difference(recess);high=c['TRAY_FLOOR']+c['SLOT_DEPTH']
    updates={};revised=[]
    # Read every original mesh before overwriting any; heights are reused only
    # at exact prepared XY coordinates, never nearest-neighbour approximated.
    source={}
    for node in config['nodes']:
        if node.get('params',{}).get('group')=='tray':
            a=np.load(ROOT/node['params']['mesh_file']);source[node['name']]=a['vertices']+node['offset']
    for node in config['nodes']:
        if node.get('params',{}).get('group')!='tray':continue
        lookup={}
        for x,y,z in source[node['name']]:
            k=(round(x,8),round(y,8));lookup[k]=max(z,lookup.get(k,-np.inf))
        def sampler(points):
            zs=[]
            for x,y in points:
                k=(round(x,8),round(y,8))
                if k not in lookup:raise ValueError(f'Fixed height sample changed: {k}')
                zs.append(lookup[k])
            return c['ELEVATION_DATUM']+(np.array(zs)-c['TRAY_FLOOR']-c['TERRAIN_BASE'])/(c['HORIZONTAL_CM_PER_M']*c['VERTICAL_EXAGGERATION'])
        ix,iy=np.array(node['params']['tile'])-1;poly=prepare.tray_polygon(box(xs[ix],ys[iy],xs[ix+1],ys[iy+1]),ix,iy,nx,ny,c)
        if c.get('FIXED_DETAILS_FLUSH'):
            mesh=prepare.make_tray(poly,recess,c,raised_regions=[(fixed,high),(frame,high+c['TRAY_FRAME_RISE'])])
        else:
            mesh=prepare.make_tray(poly,recess,c,fixed,sampler,[(frame,high+c['TRAY_FRAME_RISE']),(inset,high+c['INSET_RAISE'])])
        params=dict(node['params']);params.pop('mesh_file');params['slot_depth_cm']=c['SLOT_DEPTH'];new=[]
        r=prepare.store_mesh(node['name'],mesh,params,np.mean(mesh.bounds,axis=0).tolist(),new);updates[node['name']]=new[0];revised.append(r)
        print(node['name'],r['dimensions_mm'],r['volume_mm3'],flush=True)
    config['nodes']=[updates.get(n['name'],n) for n in config['nodes']]
    fingerprint=hashlib.sha256(json.dumps({'constants':c,'data':config['data']},sort_keys=True).encode()).hexdigest();config['prepared_fingerprint']=fingerprint
    revised_by_name={r['object']:r for r in revised};report['parts']=[revised_by_name.get(r['object'],r) for r in report['parts']];report['frame_height_mm']=(c['TRAY_FLOOR']+c['SLOT_DEPTH']+c['TRAY_FRAME_RISE'])*10;report['shared_recess_depth_mm']=c['SLOT_DEPTH']*10;report['prepared_fingerprint']=fingerprint
    report['recess_area_mm2']=recess.area*100
    report['slot_outward_offset_mm']=c['SLOT_CLEARANCE']*10
    d={'type':'Feature','geometry':mapping(recess),'properties':{'depth_mm':c['SLOT_DEPTH']*10,'outward_offset_mm':c['SLOT_CLEARANCE']*10}}
    prepare.write_json(OUT/'national_recess.geojson',d);prepare.write_json(ROOT/'model.json',config);prepare.write_json(ROOT/'spec/data_report.json',report)
    report['fixed_details_flush']=bool(c.get('FIXED_DETAILS_FLUSH'))
    report['outer_corner_radius_mm']=c.get('TRAY_OUTER_CORNER_RADIUS',0)*10
    prepare.write_json(ROOT/'spec/data_report.json',report)
    print('Rebuilt four bases; province terrain unchanged; fixed details flush' if c.get('FIXED_DETAILS_FLUSH') else 'Rebuilt four bases; province meshes and true fixed-terrain heights preserved')

if __name__=='__main__':main()
