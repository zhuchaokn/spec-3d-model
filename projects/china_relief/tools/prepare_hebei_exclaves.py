"""Recover province-owned enclosed regions from cached boundaries and DEM."""
import json,shutil
import numpy as np,shapely,rasterio,trimesh
from scipy.ndimage import map_coordinates
from pyproj import Transformer
from shapely.geometry import shape,Polygon,mapping
from shapely.ops import transform,unary_union
import prepare_print as p


def main():
    cfg=json.loads((p.ROOT/'model.json').read_text());c=cfg['constants'];group=next(g for g in cfg['printing']['province_assemblies'] if g.get('enclosed_exclave_codes'))
    codes=group['enclosed_exclave_codes'];provinces,_=p.prepare.get_provinces(cfg)
    for province in provinces:
        if province['code']==460000:province['wgs']=unary_union([g for g in p.prepare.polygons(province['wgs']) if g.bounds[3]>=c['NANSHA_MAX_LAT']])
    projection=Transformer.from_crs('EPSG:4326',cfg['data']['projection'],always_xy=True)
    projected=[transform(projection.transform,province['wgs']) for province in provinces]
    x0,y0,x1,y1=unary_union(projected).bounds;factor=c['HORIZONTAL_CM_PER_M'];origin=(x0+x1)/2
    occupied=Polygon();full={}
    for province,geom in zip(provinces,projected):
        cm=transform(lambda x,y,z=None:((np.asarray(x)-origin)*factor,(np.asarray(y)-y0)*factor),geom)
        cm=shapely.set_precision(cm,c['NUMERICAL_GAP']/10).difference(occupied)
        if not cm.is_valid:cm=unary_union(p.prepare.polygons(shapely.make_valid(cm)))
        occupied=occupied.union(cm);full[province['code']]=cm.simplify(c['NUMERICAL_GAP']/10,preserve_topology=True)
    features=json.loads((p.ROOT/'data/processed/province_print_outlines.geojson').read_text())['features']
    outlines={int(f['properties']['code']):shape(f['geometry']) for f in features}
    union=unary_union([outlines[code] for code in group['codes']]);holes=[Polygon(r) for poly in p.prepare.polygons(union) for r in poly.interiors]
    additions=[];ownership=[]
    for hole in holes:
        for code in codes:
            match=full[code].intersection(hole)
            if match.area/hole.area<.999:continue
            error=hole.difference(full[code]).area*100;assert error<.001
            additions.append((code,hole));ownership.append({'code':code,'area_mm2':hole.area*100,'bounds_mm':[v*10 for v in hole.bounds],'source_ownership_area_error_mm2':error})
            break
    assert additions and len(additions)==len(holes),'Every filled hole must be owned by the requested province'
    region=unary_union([g for _,g in additions]);assembled=union.union(region)
    assert assembled.geom_type=='Polygon' and not assembled.interiors
    geo={'type':'FeatureCollection','features':[{'type':'Feature','properties':{'province_code':code,'assembly':group['name'],'role':'enclosed_exclave'},'geometry':mapping(g)} for code,g in additions]}
    p.prepare.write_json(p.ROOT/group['exclave_geometry_file'],geo)
    fixed_path=p.ROOT/'data/processed/fixed_details.geojson';fixed_data=json.loads(fixed_path.read_text());fixed=shape(fixed_data['features'][0]['geometry']);new_fixed=fixed.difference(region)
    assert new_fixed.intersection(region).area<1e-12
    fixed_data['features'][0]['geometry']=mapping(new_fixed);p.prepare.write_json(fixed_path,fixed_data)
    nominal_path=p.ROOT/'data/processed/national_recess_nominal.geojson';nominal_data=json.loads(nominal_path.read_text());nominal=shape(nominal_data['geometry']);nominal_data['geometry']=mapping(nominal.union(region));p.prepare.write_json(nominal_path,nominal_data)
    with rasterio.open(p.ROOT/'data/processed/terrain_mosaic.tif') as ds:array=ds.read(1);affine=ds.transform
    cm_to_m=Transformer.from_crs(cfg['data']['projection'],'EPSG:3857',always_xy=True)
    def sample(points):
        points=np.asarray(points);tx,ty=cm_to_m.transform(points[:,0]/factor+origin,points[:,1]/factor+y0)
        cols=(np.asarray(tx)-affine.c)/affine.a-.5;rows=(np.asarray(ty)-affine.f)/affine.e-.5
        values=map_coordinates(array,[rows,cols],order=1,mode='constant',cval=np.nan,prefilter=False)
        assert np.isfinite(values).all()
        negative=values<0
        if np.any(negative):
            distances=shapely.distance(shapely.points(points[negative]),occupied.boundary)
            values[np.flatnonzero(negative)[distances<10000*factor]]=0
        return values
    meshes={};terrain=[]
    for code,geom in additions:
        mesh,hrange=p.prepare.build_solid(geom,sample,c['TRAY_FLOOR'],c)
        assert mesh.is_watertight and mesh.body_count==1
        meshes.setdefault(code,[]).append(mesh);terrain.append({'code':code,'elevation_range_m':list(hrange),'volume_mm3':mesh.volume*1000,'watertight':True})
    updates={}
    for code,extra in meshes.items():
        node=next(n for n in cfg['nodes'] if n.get('params',{}).get('group')=='terrain' and n['params']['code']==code)
        primary_path=p.ROOT/node['params'].get('primary_mesh_file',f'data/processed/P{code}_primary_before_exclaves.npz')
        if not primary_path.exists():shutil.copy2(p.ROOT/node['params']['mesh_file'],primary_path)
        data=np.load(primary_path);primary=trimesh.Trimesh(vertices=data['vertices']+node['offset'],faces=data['faces'],process=False)
        combined=trimesh.util.concatenate([primary,*extra]);params=dict(node['params']);params.pop('mesh_file');params['primary_mesh_file']=str(primary_path.relative_to(p.ROOT));params['enclosed_exclave_count']=len(extra)
        nodes=[];p.prepare.store_mesh(node['name'],combined,params,node['offset'],nodes);updates[node['name']]=nodes[0]
    cfg['nodes']=[updates.get(n['name'],n) for n in cfg['nodes']]
    p.prepare.write_json(p.ROOT/'model.json',cfg)
    report=json.loads((p.ROOT/'spec/data_report.json').read_text());report['fixed_detail_component_count']=len(p.prepare.polygons(new_fixed));report['enclosed_hebei_exclaves']=ownership;p.prepare.write_json(p.ROOT/'spec/data_report.json',report)
    p.prepare.write_json(p.ROOT/'spec/hebei_exclave_report.json',{'assembly':group['name'],'province_code':130000,'region_count':len(additions),'group_holes_before':len(holes),'group_holes_after':len(assembled.interiors),'regions':ownership,'terrain':terrain,'removed_fixed_area_mm2':fixed.difference(new_fixed).area*100,'other_fixed_geometry_unchanged':True,'source_boundary':cfg['data']['boundary'],'dem_file':'data/processed/terrain_mosaic.tif'})
    print('Recovered',len(additions),'Hebei enclosed regions; zero assembly holes; restored DEM and removed fixed posts')

if __name__=='__main__':main()
