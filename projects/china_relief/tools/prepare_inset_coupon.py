"""Small real-inset coupon for checking depth, thicker lines and larger type."""
import json,zipfile
import numpy as np
from shapely.geometry import shape,box
from shapely.affinity import translate
import prepare_print as p


def main():
    config=json.loads((p.ROOT/'model.json').read_text());c=config['constants'];pr=config['printing']
    report=json.loads((p.ROOT/'spec/data_report.json').read_text());panel=box(*report['inset']['panel_bounds_cm'])
    bounds=report['inset']['text_bounds_cm']['南沙群岛'];size=pr['inset_test_size_mm']/10
    cx=np.clip((bounds[0]+bounds[2])/2,panel.bounds[0]+size/2,panel.bounds[2]-size/2)
    cy=np.clip(bounds[1]+size/2-c['INSET_PADDING'],panel.bounds[1]+size/2,panel.bounds[3]-size/2)
    radius=c['TRAY_OUTER_CORNER_RADIUS'];outline=box(cx-size/2,cy-size/2,cx+size/2,cy+size/2).buffer(-radius,join_style=2).buffer(radius,quad_segs=c['TRAY_CORNER_QUAD_SEGMENTS'])
    assert outline.covers(box(*bounds)), 'Crop must contain the complete Nansha label'
    marks=shape(json.loads((p.ROOT/'data/processed/south_sea_inset.geojson').read_text())['geometry']).intersection(outline)
    marks=translate(marks,-cx,-cy);outline=translate(outline,-cx,-cy);sea=outline.difference(marks)
    top=c['TRAY_FLOOR']+c['SLOT_DEPTH'];bottom=top-pr['inset_inlay_thickness_mm']/10;skin=top-pr['sea_color_thickness_mm']/10
    parts=[('小样_灰色底材',pr['base_filament_id'],p.prism(outline,0,bottom)),('小样_灰色承托层',pr['base_filament_id'],p.prism(sea,bottom,skin)),('小样_蓝色海面',pr['sea_filament_id'],p.prism(sea,skin,top)),('小样_嵌色南沙文字与符号',pr['inset_filament_id'],p.prism(marks,bottom,top))]
    assert abs(sum(m.volume for _,_,m in parts)-outline.area*top)<1e-8
    for _,_,m in parts:m.vertices*=10
    with zipfile.ZipFile(p.ROOT/'output/china_relief_P2S_9plates_robust_inset_R5.3mf') as z:settings=json.loads(z.read('Metadata/project_settings.config'))
    settings['layer_height']=str(pr['base_layer_height_mm']);settings['print_settings_id']=f"{pr['base_layer_height_mm']:.2f}mm Standard @BBL P2S";settings['wall_generator']=pr['multicolor_wall_generator'];settings['min_bead_width']=str(pr['multicolor_min_bead_width_percent'])+'%'
    item={'name':'南海嵌色50mm实图小样','parts':parts,'x':pr['plate_margin_mm']+pr['inset_test_size_mm']/2,'y':pr['plate_margin_mm']+pr['inset_test_size_mm']/2,'rotate':False}
    target=p.ROOT/'output/china_relief_south_sea_50mm_test.3mf';p.write_project(target,[item],[x['id'] for x in pr['colors']],settings)
    print('Saved real-inset 50 mm test coupon:',target)

if __name__=='__main__':main()
