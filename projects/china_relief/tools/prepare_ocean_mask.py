"""Align Natural Earth physical coastlines to the existing projected puzzle.
Uses the model's original province data only to recover its exact XY transform.
"""
from pathlib import Path
import json,zipfile,hashlib
import numpy as np
import shapefile
import shapely
from shapely.geometry import shape,box,Polygon,mapping
from shapely.ops import transform,unary_union
from pyproj import Transformer
import prepare
ROOT=Path(__file__).resolve().parents[1]


def main():
    config=json.loads((ROOT/'model.json').read_text());c=config['constants'];settings=config['printing']['ocean_mask'];archive=ROOT/settings['archive_file'];raw=archive.parent/settings['dataset_name'];raw.mkdir(exist_ok=True)
    with zipfile.ZipFile(archive) as z:
        for entry in z.namelist():
            if Path(entry).name==entry:z.extract(entry,raw)
    provinces,_=prepare.get_provinces(config)
    land=unary_union([p for row in provinces for p in prepare.polygons(row['wgs']) if not(row['code']==460000 and p.bounds[3]<c['NANSHA_MAX_LAT'])])
    projection=Transformer.from_crs('EPSG:4326',config['data']['projection'],always_xy=True);inverse=Transformer.from_crs(config['data']['projection'],'EPSG:4326',always_xy=True)
    x0,y0,x1,y1=transform(projection.transform,land).bounds;factor=c['MAP_WIDTH']/(x1-x0);assert np.isclose(factor,c['HORIZONTAL_CM_PER_M'],rtol=1e-12)
    report=json.loads((ROOT/'spec/data_report.json').read_text());bx0,by0,bx1,by1=report['tray_bounds_cm'];board=box(bx0,by0,bx1,by1)
    xx,yy=np.meshgrid(np.linspace(bx0,bx1,settings['bounds_sample_count']),np.linspace(by0,by1,settings['bounds_sample_count']));lon,lat=inverse.transform(xx.ravel()/factor+(x0+x1)/2,yy.ravel()/factor+y0);margin=settings['geographic_clip_margin_deg'];region=box(min(lon)-margin,min(lat)-margin,max(lon)+margin,max(lat)+margin)
    reader=shapefile.Reader(str(raw/(settings['dataset_name']+'.shp')));parts=[]
    for row in reader.iterShapes():
        if not box(*row.bbox).intersects(region):continue
        g=shapely.make_valid(shape(row.__geo_interface__))
        # Inland water stays neutral gray; only the external coast defines sea.
        g=unary_union([Polygon(p.exterior) for p in prepare.polygons(g)]).intersection(region)
        if not g.is_empty:parts.append(g)
    projected=transform(projection.transform,unary_union(parts))
    to_cm=lambda x,y,z=None:((np.asarray(x)-(x0+x1)/2)*factor,(np.asarray(y)-y0)*factor)
    world=transform(to_cm,projected).intersection(board).simplify(settings['simplify_mm']/10,preserve_topology=True)
    ocean=board.difference(world)
    # The inset is a separate cartographic sea panel, not the land beneath its
    # arbitrary placement on the main-map coordinate plane.
    panel=box(*report['inset']['panel_bounds_cm']);ocean=ocean.union(panel).intersection(board)
    prepare.write_json(ROOT/settings['land_mask_file'],{'type':'Feature','properties':{'source':settings['source_url'],'crs':config['data']['projection'],'units':'cm','sha256':hashlib.sha256(archive.read_bytes()).hexdigest()},'geometry':mapping(world)})
    prepare.write_json(ROOT/settings['sea_mask_file'],{'type':'Feature','properties':{'inset_panel_is_cartographic':True},'geometry':mapping(ocean)})
    prepare.write_json(ROOT/'spec/ocean_mask_report.json',{'source':settings['source_url'],'license':settings['license'],'source_scale':settings['source_scale'],'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'land_area_mm2':world.area*100,'ocean_area_mm2':ocean.difference(panel).area*100,'main_ocean_over_land_mm2':ocean.difference(panel).intersection(world).area*100,'map_transform_cm_per_m':factor,'projected_origin_m':[(x0+x1)/2,y0],'clip_bounds_lonlat':list(region.bounds),'simplify_mm':settings['simplify_mm']})
    assert ocean.difference(panel).intersection(world).area<1e-10
    print('Aligned physical coastlines: main ocean / neighboring land overlap is zero',flush=True)

if __name__=='__main__':main()
