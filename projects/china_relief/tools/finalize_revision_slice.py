"""Normalize P2S CLI metadata and check all nine sliced plates, without printing."""
import argparse,hashlib,json,re,zipfile,xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
from prepare_print import mark_print_overrides
from verify_3mf_meshes import verify
ROOT=Path(__file__).resolve().parents[1]


def main():
    a=argparse.ArgumentParser();a.add_argument('native',type=Path);a.add_argument('destination',type=Path);a.add_argument('--coupon',action='store_true');args=a.parse_args()
    count=1 if args.coupon else 9
    config=json.loads((ROOT/'model.json').read_text());pr=config['printing'];result=json.loads((args.native.parent/'result.json').read_text());assert result['return_code']==0 and len(result['sliced_plates'])==count
    machine=json.loads(Path('/Applications/BambuStudio.app/Contents/Resources/profiles/BBL/machine/Bambu Lab P2S.json').read_text())
    with zipfile.ZipFile(args.native) as src,zipfile.ZipFile(args.destination,'w',zipfile.ZIP_DEFLATED) as dst:
        for entry in src.namelist():
            content=src.read(entry)
            if entry=='Metadata/slice_info.config':
                xml=ET.fromstring(content)
                for e in xml.findall("plate/metadata[@key='printer_model_id']"):e.set('value',machine['model_id'])
                # CLI has no reliable first-layer time and can emit garbage floats.
                for plate in xml.findall('plate'):
                    e=plate.find("metadata[@key='first_layer_time']")
                    if e is not None:plate.remove(e)
                content=ET.tostring(xml,encoding='utf-8',xml_declaration=True)
            if entry=='Metadata/project_settings.config':
                settings=json.loads(content);mark_print_overrides(settings,len(pr['colors']));content=json.dumps(settings,ensure_ascii=False).encode()
            dst.writestr(entry,content)
    records=[]
    with zipfile.ZipFile(args.destination) as z:
        settings=json.loads(z.read('Metadata/project_settings.config'));assert settings['printer_settings_id']==pr['printer'] and settings['filament_colour']==[c['hex'] for c in pr['colors']]
        assert settings['enable_prime_tower']=='0' and settings['sparse_infill_density']=='5%' and settings['sparse_infill_pattern']=='gyroid'
        cfg=ET.fromstring(z.read('Metadata/model_settings.config'));assert len(cfg.findall('plate'))==count
        si=ET.fromstring(z.read('Metadata/slice_info.config'));assert len(si.findall('plate'))==count
        for i,plate in enumerate(si.findall('plate'),1):
            meta={m.get('key'):m.get('value') for m in plate.findall('metadata')};assert meta['outside']=='false' and meta['printer_model_id']==machine['model_id']
            name=f'Metadata/plate_{i}.gcode';g=z.read(name)
            assert hashlib.md5(g).hexdigest()==z.read(name+'.md5').decode().strip().lower()
            assert b'; enable_prime_tower = 0' in g and b'; sparse_infill_density = 5%' in g
            assert not re.search(rb'; FEATURE: (?:Prime|Wipe) tower',g,re.I)
            heights=[float(h) for h in re.findall(rb'; CHANGE_LAYER\r?\n; Z_HEIGHT: [^\n]+\r?\n; LAYER_HEIGHT: ([0-9.]+)',g)]
            expected=pr['base_layer_height_mm'] if args.coupon or i in [2,3,4,5] else pr['card_layer_height_mm']
            assert heights and np.allclose(heights[1:],expected,atol=1e-5),(i,heights[:10])
            p=result['sliced_plates'][i-1]
            if args.coupon or i in [2,3,4,5]:assert not p['warning_message']
            records.append({'plate':i,'grams':sum(f['total_used_g'] for f in p['filaments']),'colors':[f['id'] for f in p['filaments']],'filament_changes':p['filament_change_times'],'layer_height_mm':expected,'slice_warning':p['warning_message'],'gcode_md5_matches':True,'no_tower':True})
        # Ivory exists only in the configured flush inlay layers.
        inset=si.findall('plate')[0 if args.coupon else 2];ranges=[]
        for e in inset.findall('layer_filament_lists/layer_filament_list'):
            if '2' in e.get('filament_list','').split():ranges.append(e.get('layer_ranges'))
        high=(config['constants']['TRAY_FLOOR']+config['constants']['SLOT_DEPTH'])*10
        last=round(high/pr['base_layer_height_mm'])-1
        first=last-round(pr['inset_inlay_thickness_mm']/pr['base_layer_height_mm'])+1
        actual_layers=set()
        for value in ranges:
            limits=[int(x) for x in value.split()]
            for start,end in zip(limits[::2],limits[1::2]):actual_layers.update(range(start,end+1))
        assert actual_layers==set(range(first,last+1)),ranges
    report={'slice_success':True,'plate_count':count,'production_grams':sum(p['grams'] for p in records[1:]),'test_plate_grams':records[0]['grams'],'inset_color_layer_indices_zero_based':sorted(actual_layers),'new_bases_without_floating_warnings':True,'verified_actual_3mf_closed_meshes':verify(args.destination),'sha256':hashlib.sha256(args.destination.read_bytes()).hexdigest(),'plates':records}
    filename='inset_coupon_report.json' if args.coupon else 'flush_slice_report.json'
    (ROOT/'spec'/filename).write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
