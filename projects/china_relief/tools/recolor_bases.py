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

if __name__=='__main__':main()
