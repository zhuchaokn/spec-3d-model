"""Verify stored blue-print surfaces against physical land and reference points."""
from pathlib import Path
import json
import numpy as np
import shapely
from shapely.geometry import shape,Point,box
from pyproj import Transformer
import prepare
ROOT=Path(__file__).resolve().parents[1]


def main():
    config=json.loads((ROOT/'model.json').read_text());pr=config['printing'];settings=pr['ocean_mask'];mask_report=json.loads((ROOT/'spec/ocean_mask_report.json').read_text());data_report=json.loads((ROOT/'spec/data_report.json').read_text())
    land=shape(json.loads((ROOT/settings['land_mask_file']).read_text())['geometry']);sea=shape(json.loads((ROOT/settings['sea_mask_file']).read_text())['geometry']);board=box(*data_report['tray_bounds_cm']);panel=box(*data_report['inset']['panel_bounds_cm'])
    projection=Transformer.from_crs('EPSG:4326',config['data']['projection'],always_xy=True);origin=np.array(mask_report['projected_origin_m']);factor=mask_report['map_transform_cm_per_m'];samples=[]
    for kind,key in [('land','validation_land_points_lonlat'),('sea','validation_sea_points_lonlat')]:
        for name,lonlat in settings[key].items():
            point=Point((np.array(projection.transform(*lonlat))-origin)*factor)
            if not board.contains(point) or panel.contains(point):continue
            assert (land.contains(point) and not sea.contains(point)) if kind=='land' else (sea.contains(point) and not land.contains(point)),name
            samples.append({'name':name,'expected':kind,'lonlat':lonlat,'matched':True})
    manifest=json.loads((ROOT/'output/printing/print_manifest.json').read_text());checks=[];height=(config['constants']['TRAY_FLOOR']+config['constants']['SLOT_DEPTH'])*10;foreign_land=land.difference(panel)
    for name,base in manifest['multicolor_bases'].items():
        blue=next((part for part in base['parts'] if part['color']==pr['sea_filament_id']),None);area=overlap=0
        if blue:
            arrays=np.load(ROOT/'output/printing'/(blue['name']+'.npz'));v=arrays['vertices']+arrays['assembly_offset_mm'];tri=v[arrays['faces']];cross=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);top=np.all(np.isclose(tri[:,:,2],height,atol=1e-6),axis=1)&(cross[:,2]>0)
            area=float(cross[top,2].sum()/2);assert abs(area-base['sea_surface_area_mm2'])<.001
            assert np.allclose([v[:,2].min(),v[:,2].max()],[height-pr['sea_color_thickness_mm'],height])
            polygons=shapely.polygons(tri[top,:,:2]/10);overlap=float(np.sum(shapely.area(shapely.intersection(polygons,foreign_land)))*100);assert overlap<.001,(name,overlap)
        else:assert base['sea_surface_area_mm2']==0
        checks.append({'object':name,'actual_blue_top_area_mm2':area,'actual_blue_top_over_land_mm2':overlap,'volume_delta_mm3':float(base['volume_delta_mm3']),'color_count':len(base['parts'])})
    assert len(checks)==4
    prepare.write_json(ROOT/'spec/sea_color_report.json',{'only_physical_ocean_blue':True,'neighboring_land_gray':True,'main_ocean_over_land_mm2':mask_report['main_ocean_over_land_mm2'],'land_and_sea_reference_checks':samples,'bases':checks})
    print('Verified actual blue triangles: no neighboring-land overlap; five land and four sea reference points matched')

if __name__=='__main__':main()
