"""Check the actual prepared surfaces against contour, frame and inset areas."""
import json
from pathlib import Path
import numpy as np
from shapely.geometry import shape, box
from shapely.ops import unary_union
from prepare import tray_polygon, write_json

ROOT=Path(__file__).resolve().parents[1]


def main():
    config=json.loads((ROOT/'model.json').read_text()); c=config['constants']
    report=json.loads((ROOT/'spec/data_report.json').read_text())
    processed=ROOT/'data/processed'
    recess=shape(json.loads((processed/'national_recess.geojson').read_text())['geometry'])
    fixed=shape(json.loads((processed/'fixed_details.geojson').read_text())['features'][0]['geometry'])
    inset=shape(json.loads((processed/'south_sea_inset.geojson').read_text())['geometry'])
    nodes=[n for n in config['nodes'][:-1] if n['params']['group']=='tray']
    nx=max(n['params']['tile'][0] for n in nodes); ny=max(n['params']['tile'][1] for n in nodes)
    width,height=np.array(report['tray_dimensions_mm'])/10
    x0,y0,x1,y1=report['tray_bounds_cm']
    assert [nx,ny]==config['data']['required_tray_grid']==[2,2]
    xs=np.linspace(x0,x1,nx+1); ys=np.linspace(y0,y1,ny+1)
    inner=box(x0+c['TRAY_FRAME_WIDTH'],y0+c['TRAY_FRAME_WIDTH'],
              x1-c['TRAY_FRAME_WIDTH'],y1-c['TRAY_FRAME_WIDTH']).buffer(c['NUMERICAL_GAP'],join_style=2)
    frame=box(x0,y0,x1,y1).difference(inner).difference(recess)
    low=c['TRAY_FLOOR']; high=low+c['SLOT_DEPTH']
    levels=[low,high,high+c['TRAY_FRAME_RISE'],high+c['INSET_RAISE']]
    regions=[recess.difference(fixed),box(x0,y0,x1,y1).difference(unary_union([recess,frame,inset])),frame,inset]
    if c.get('FIXED_DETAILS_FLUSH'):
        levels=[low,high,high+c['TRAY_FRAME_RISE']]
        regions=[recess.difference(fixed),box(x0,y0,x1,y1).difference(unary_union([recess,frame])).union(fixed),frame]
    checks=[]
    for node in nodes:
        ix,iy=np.array(node['params']['tile'])-1
        outline=tray_polygon(box(xs[ix],ys[iy],xs[ix+1],ys[iy+1]),ix,iy,nx,ny,c)
        data=np.load(ROOT/node['params']['mesh_file'])
        vertices=data['vertices']+np.array(node['offset']); triangles=vertices[data['faces']]
        cross=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0])
        actual=[]; expected=[]
        for level,region in zip(levels,regions):
            mask=np.all(np.isclose(triangles[:,:,2],level,atol=1e-9,rtol=0),axis=1)&(cross[:,2]>0)
            actual.append(float(np.sum(cross[mask,2])/2*100))
            expected.append(outline.intersection(region).area*100)
        assert np.allclose(actual,expected,atol=.001,rtol=0),(node['name'],actual,expected)
        checks.append({'object':node['name'],'surface_order':['recess_floor','flush_platform','raised_frame'] if c.get('FIXED_DETAILS_FLUSH') else ['recess_floor','platform','raised_frame','fixed_inset'],
                       'actual_areas_mm2':actual,'expected_areas_mm2':expected,'matches':True})
    inset_report=report['inset']
    panel=inset_report['panel_bounds_cm']
    assert np.isclose(panel[2],c['MAP_WIDTH']/2+c['INSET_RIGHT_OFFSET_FROM_MAP'])
    if config['data']['south_sea_inset']['placement']=='bottom_right':
        assert np.isclose(panel[1],y0+c['TRAY_FRAME_WIDTH']+c['INSET_MARGIN'])
    nansha=[r for r in inset_report['records'] if r['code']==460000 and r['source_bounds_lonlat'][3]<c['NANSHA_MAX_LAT']]
    assert len(nansha)==report['omitted_nansha_component_count']==99
    assert inset_report['dash_count']==10 and inset_report['hainan_source_component_count']==133
    assert inset_report['omitted_source_components']==0
    assert report['card_outside_recess_mm2']<1e-6
    assert inset.intersection(recess).area<1e-8
    nominal=shape(json.loads((processed/'national_recess_nominal.geojson').read_text())['geometry'])
    expected_recess=nominal.buffer(c['SLOT_CLEARANCE'],quad_segs=24,join_style='round')
    assert recess.symmetric_difference(expected_recess).area<1e-10
    assert nominal.difference(recess).area<1e-10
    gap=min(__import__('shapely').geometry.Point(xy).distance(recess.boundary)*10 for p in __import__('prepare').polygons(nominal) for xy in p.exterior.coords)
    assert gap>=c['SLOT_CLEARANCE']*10-.001,gap
    write_json(ROOT/'spec/recess_report.json',{'slot_depth_mm':c['SLOT_DEPTH']*10,'slot_outward_offset_mm':c['SLOT_CLEARANCE']*10,'minimum_nominal_outer_vertex_clearance_mm':gap,
               'frame_rise_above_platform_mm':c['TRAY_FRAME_RISE']*10,
               'nansha_components_restored_in_inset':len(nansha),'inset_source_components':inset_report['source_component_count'],
               'inset_overlaps_main_recess':False,'tiles':checks})
    print('Verified contour floors, raised frame and inset surfaces; all 99 Nansha components included')


if __name__=='__main__': main()
