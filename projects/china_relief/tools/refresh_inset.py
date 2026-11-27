"""Regenerate only inset XY cartography; leave terrain and base geometry intact."""
import json
from pyproj import Transformer
from shapely.geometry import box,mapping
import inset,prepare


def main():
    config=json.loads(prepare.MODEL.read_text())
    report=json.loads((prepare.PROJ/'spec/data_report.json').read_text())
    projection=Transformer.from_crs('EPSG:4326',config['data']['projection'],always_xy=True)
    panel=box(*report['inset']['panel_bounds_cm'])
    geometry,result=inset.build(config,prepare.PROJ/config['data']['boundary'],panel,projection,prepare.gcj_inverse)
    assert result['records']==report['inset']['records']
    report['inset']=result;report['prepared_fingerprint']=config['prepared_fingerprint']
    prepare.write_json(prepare.OUT/'south_sea_inset.geojson',{'type':'Feature','properties':{'role':'fixed_inset'},'geometry':mapping(geometry)})
    prepare.write_json(prepare.PROJ/'spec/inset_report.json',result)
    prepare.write_json(prepare.PROJ/'spec/data_report.json',report)
    print('Retained all',result['source_component_count'],'source components and',result['dash_count'],'dash segments; inset bounds:',geometry.bounds)

if __name__=='__main__':main()
