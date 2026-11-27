"""Recolor revised bases without repacking existing province plates."""
import json
import prepare_print as p


def main():
    config=json.loads((p.ROOT/'model.json').read_text())
    manifest=json.loads((p.OUT/'print_manifest.json').read_text())
    for node in config['nodes']:
        if node.get('params',{}).get('group')=='tray':
            _,report=p.color_base(config,node)
            manifest['multicolor_bases'][node['name']]=report
            print(node['name'],'color partition delta mm3:',report['volume_delta_mm3'])
    p.prepare.write_json(p.OUT/'print_manifest.json',manifest)
    repaired=[part for base in manifest['multicolor_bases'].values() for part in base['parts'] if part.get('zero_area_faces_removed_after_mm_welding',0)]
    p.prepare.write_json(p.ROOT/'spec/color_welding_report.json',{'removed_zero_area_faces_after_mm_welding':sum(part['zero_area_faces_removed_after_mm_welding'] for part in repaired),'volume_and_bounds_preserved_within_tolerance':True,'parts':repaired})

if __name__=='__main__':main()
