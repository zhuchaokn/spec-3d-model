"""Prepare Bambu P2S color-part projects; all physical settings in model.json.
Uses official installed Bambu profiles, preserving real P2S machine G-code.
No printer communication and no rendering/screenshot commands.
"""
import json, sys, zipfile, copy, subprocess, collections
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
import trimesh
from shapely.geometry import shape, box
from shapely.ops import unary_union
import prepare

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/printing'
# Bambu 2.6 stores nozzle variants per filament, indexed by filament_self_index.
FILAMENT_VARIANT_KEYS=set(['filament_flow_ratio', 'filament_max_volumetric_speed', 'filament_ramming_volumetric_speed', 'filament_pre_cooling_temperature', 'filament_ramming_travel_time', 'filament_ramming_volumetric_speed_nc', 'filament_pre_cooling_temperature_nc', 'filament_ramming_travel_time_nc', 'filament_extruder_variant', 'filament_retraction_length', 'filament_retract_length_nc', 'filament_retract_length_toolchange', 'filament_retract_restart_extra_toolchange', 'filament_z_hop', 'filament_z_hop_types', 'filament_retract_restart_extra', 'filament_retraction_speed', 'filament_deretraction_speed', 'filament_retraction_minimum_travel', 'filament_retract_when_changing_layer', 'filament_wipe', 'filament_wipe_distance', 'filament_retract_before_wipe', 'filament_long_retractions_when_cut', 'filament_retraction_distances_when_cut', 'long_retractions_when_ec', 'retraction_distances_when_ec', 'nozzle_temperature_initial_layer', 'nozzle_temperature', 'filament_flush_volumetric_speed', 'filament_flush_temp', 'filament_flush_temp_fast', 'filament_enable_overhang_speed', 'filament_bridge_speed', 'filament_overhang_1_4_speed', 'filament_overhang_2_4_speed', 'filament_overhang_3_4_speed', 'filament_overhang_4_4_speed', 'filament_overhang_totally_speed', 'override_process_overhang_speed', 'volumetric_speed_coefficients', 'filament_adaptive_volumetric_speed', 'filament_preheat_temperature_delta', 'filament_cooling_before_tower', 'slow_down_min_speed'])
CORE='http://schemas.microsoft.com/3dmanufacturing/core/2015/02'
PROD='http://schemas.microsoft.com/3dmanufacturing/production/2015/06'
ET.register_namespace('',CORE)
ET.register_namespace('p',PROD)
# Bambu GUI only reapplies preset edits listed in this field when opening 3MF.
# Values still come from model.json / resolved official profiles.
GUI_PROCESS_OVERRIDE_KEYS=['layer_height','initial_layer_print_height','wall_loops','sparse_infill_density','sparse_infill_pattern','top_shell_layers','bottom_shell_layers','xy_contour_compensation','elefant_foot_compensation','brim_type','brim_width','skirt_loops','enable_support','enable_prime_tower','flush_into_infill','print_sequence']
OBJECT_LIGHTWEIGHT_KEYS=['wall_loops','sparse_infill_density','sparse_infill_pattern','top_shell_layers','bottom_shell_layers']


def mark_print_overrides(settings,count):
    flags=list(settings.get('different_settings_to_system',[]))
    flags=(flags+['']*(count+2))[:count+2]
    flags[0]=';'.join(sorted((set(flags[0].split(';'))|set(GUI_PROCESS_OVERRIDE_KEYS))-{''}))
    settings['different_settings_to_system']=flags



def mesh_for(node):
    a=np.load(ROOT/node['params']['mesh_file'])
    return trimesh.Trimesh(vertices=(a['vertices']+node['offset'])*10,faces=a['faces'],process=False)


def prism(geom,lo,hi):
    meshes=[]
    for p in prepare.polygons(geom):
        v,f=prepare.triangulate(p); n=len(v)
        edges=np.concatenate([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]])
        _,inv,cnt=np.unique(np.sort(edges,axis=1),axis=0,return_inverse=True,return_counts=True)
        boundary=edges[cnt[inv]==1]
        sides=[]
        for i,j in boundary:sides.extend([[n+i,i,j],[n+i,j,n+j]])
        meshes.append(trimesh.Trimesh(vertices=np.vstack([np.c_[v,np.full(n,lo)],np.c_[v,np.full(n,hi)]]),faces=np.vstack([f[:,[0,2,1]],f+n,sides]),process=False))
    m=trimesh.util.concatenate(meshes)
    assert m.is_watertight and m.is_winding_consistent and m.volume>0
    return m


def color_base(config,node):
    c=config['constants']; pr=config['printing']
    report=json.loads((ROOT/'spec/data_report.json').read_text())
    x0,y0,x1,y1=report['tray_bounds_cm']; xs=np.linspace(x0,x1,3); ys=np.linspace(y0,y1,3)
    ix,iy=np.array(node['params']['tile'])-1
    poly=prepare.tray_polygon(box(xs[ix],ys[iy],xs[ix+1],ys[iy+1]),ix,iy,2,2,c)
    def geo(file,key=None):
        d=json.loads((ROOT/'data/processed'/file).read_text())
        return shape(d['features'][0]['geometry'] if key else d['geometry'])
    wells=geo('national_recess.geojson'); fixed=geo('fixed_details.geojson',True); marks=geo('south_sea_inset.geojson')
    inner=box(x0+c['TRAY_FRAME_WIDTH'],y0+c['TRAY_FRAME_WIDTH'],x1-c['TRAY_FRAME_WIDTH'],y1-c['TRAY_FRAME_WIDTH']).buffer(c['NUMERICAL_GAP'],join_style=2)
    frame=box(x0,y0,x1,y1).difference(inner).difference(wells)
    original=mesh_for(node);verts=original.vertices/10
    lookup={}
    for x,y,z in verts:
        key=(round(x,8),round(y,8));lookup[key]=max(z,lookup.get(key,-float('inf')))
    def sampler(points):
        heights=[]
        for x,y in points:
            key=(round(x,8),round(y,8))
            if key not in lookup:raise ValueError(f'New terrain sample {key}; must use actual DEM')
            heights.append(lookup[key])
        return c['ELEVATION_DATUM']+(np.array(heights)-c['TRAY_FLOOR']-c['TERRAIN_BASE'])/(c['HORIZONTAL_CM_PER_M']*c['VERTICAL_EXAGGERATION'])
    high=c['TRAY_FLOOR']+c['SLOT_DEPTH'];bottom=high-pr['sea_color_thickness_mm']/10
    ocean_mask=geo(Path(pr['ocean_mask']['sea_mask_file']).name)
    platform=poly.difference(unary_union([wells,frame]))
    local_marks=marks.intersection(poly)
    if c.get('FIXED_DETAILS_FLUSH'):
        assert pr['inset_inlay_thickness_mm']==pr['sea_color_thickness_mm']
        platform=platform.union(fixed.intersection(poly))
        # Source islands remain land where the coarser world mask misses them.
        sea_region=platform.intersection(ocean_mask).difference(fixed).difference(local_marks)
        land_region=platform.difference(unary_union([sea_region,local_marks]))
    else:
        sea_region=platform.intersection(ocean_mask);land_region=platform.difference(sea_region)
    cc=copy.deepcopy(c);cc['SLOT_DEPTH']=bottom-c['TRAY_FLOOR']
    if c.get('FIXED_DETAILS_FLUSH'):
        gray=prepare.make_tray(poly,wells,cc,raised_regions=[(fixed,bottom),(frame,high+c['TRAY_FRAME_RISE'])])
    else:
        gray=prepare.make_tray(poly,wells,cc,fixed,sampler,[(frame,high+c['TRAY_FRAME_RISE'])])
    solids=[('灰色结构',pr['base_filament_id'],gray)]
    # Adjacent closed volumes share one Bambu object. Keeping the gray land skin
    # separate avoids microscopic Boolean remnants around inset lettering.
    if not land_region.is_empty:solids.append(('灰色陆地表层',pr['base_filament_id'],prism(land_region,bottom,high)))
    if not sea_region.is_empty:solids.append(('蓝色海面',pr['sea_filament_id'],prism(sea_region,bottom,high)))
    if not local_marks.is_empty:
        lo,hi=(bottom,high) if c.get('FIXED_DETAILS_FLUSH') else (high,high+c['INSET_RAISE'])
        solids.append(('南海诸岛_岛礁文字',pr['inset_filament_id'],prism(local_marks,lo,hi)))
    for _,_,m in solids:m.vertices*=10
    delta=sum(m.volume for _,_,m in solids)-original.volume
    assert abs(delta)<pr['ocean_mask']['partition_volume_tolerance_mm3'],delta
    offset=(original.bounds[0]+original.bounds[1])/2; offset[2]=original.bounds[0,2]
    parts=[]
    for role,color,m in solids:
        name=node['name']+'_'+role
        m.vertices-=offset
        m.export(OUT/(name+'.stl'))
        np.savez_compressed(OUT/(name+'.npz'),vertices=m.vertices,faces=m.faces,assembly_offset_mm=offset)
        parts.append((name,color,m))
    return parts,{'object':node['name'],'volume_delta_mm3':delta,'sea_surface_area_mm2':sea_region.area*100,'sea_thickness_mm':pr['sea_color_thickness_mm'],'parts':[{'name':n,'color':i,'volume_mm3':float(m.volume),'watertight':bool(m.is_watertight),'triangles':len(m.faces)} for n,i,m in parts]}


def coloring(config,nodes):
    features=json.loads((ROOT/'data/processed/province_print_outlines.geojson').read_text())['features']
    geoms={int(f['properties']['code']):shape(f['geometry']) for f in features if f['properties']['role']=='removable_card'}
    graph={n['params']['code']:set() for n in nodes}
    codes=sorted(graph)
    for i,a in enumerate(codes):
        for b in codes[i+1:]:
            if geoms[a].boundary.intersection(geoms[b].boundary).length>.005:
                graph[a].add(b);graph[b].add(a)
    ids=config['printing']['province_filament_ids']
    assigned=config['printing'].get('province_color_assignments')
    if assigned:
        colors={int(code):color for code,color in assigned.items()}
        assert set(colors)==set(graph) and all(color in ids for color in colors.values())
        assert all(colors[a]!=colors[b] for a in graph for b in graph[a])
        target=config['printing']['province_color_balance']['target_count_per_color']
        assert all(sum(v==color for v in colors.values())==target for color in ids)
        return colors,[[a,b] for a in graph for b in graph[a] if a<b]
    colors={}
    def solve():
        if len(colors)==len(graph):return True
        a=max((k for k in graph if k not in colors),key=lambda k:(len({colors[v] for v in graph[k] if v in colors}),len(graph[k]),-k))
        used={colors[v] for v in graph[a] if v in colors}
        for color in ids:
            if color not in used:
                colors[a]=color
                if solve():return True
                del colors[a]
        return False
    assert solve()
    assert all(colors[a]!=colors[b] for a in graph for b in graph[a])
    return colors,[[a,b] for a in graph for b in graph[a] if a<b]


def pack(items,config):
    pr=config['printing']; margin=pr['plate_margin_mm'];size=config['constants']['PRINT_BED']*10;gap=pr['object_spacing_mm']+2*pr['brim_width_mm']
    bins=[]
    for name,parts in sorted(items,key=lambda x:-np.prod(trimesh.util.concatenate([p[2] for p in x[1]]).extents[:2])):
        dims=trimesh.util.concatenate([p[2] for p in parts]).extents[:2]
        choices=[]
        for bi,b in enumerate(bins):
            for fi,(x,y,w,h) in enumerate(b['free']):
                for rotate in [False,True]:
                    dx,dy=dims[::-1] if rotate else dims
                    if dx<=w+1e-6 and dy<=h+1e-6:choices.append((w*h-dx*dy,bi,fi,rotate,dx,dy))
        if not choices:
            bins.append({'free':[(margin,margin,size-2*margin,size-2*margin)],'items':[]});bi=len(bins)-1
            dx,dy=dims
            assert max(dims)<=size-2*margin,(name,dims)
            choices=[(0,bi,0,False,dx,dy)]
        _,bi,fi,rotate,dx,dy=min(choices)
        b=bins[bi];x,y,w,h=b['free'].pop(fi)
        b['items'].append({'name':name,'parts':parts,'x':x+dx/2,'y':y+dy/2,'rotate':rotate,'bbox':[x,y,x+dx,y+dy]})
        if w-dx-gap>0:b['free'].append((x+dx+gap,y,w-dx-gap,h))
        if h-dy-gap>0:b['free'].append((x,y+dy+gap,dx,h-dy-gap))
    return bins


def resolved_profiles(config):
    folder=Path('/Applications/BambuStudio.app/Contents/Resources/profiles/BBL');index={}
    for p in folder.rglob('*.json'):
        d=json.loads(p.read_text())
        if 'name' in d:index[d['name']]=d
    def resolve(name):
        d=index[name];r=resolve(d['inherits']) if d.get('inherits') else {}
        for n in d.get('include',[]):r.update(resolve(n))
        r.update({k:v for k,v in d.items() if k not in ['inherits','include']});return r
    pr=config['printing']
    machine=resolve(pr['printer']);filament=resolve(pr['material'])
    processes={}
    for kind,key in [('base','base_layer_height_mm'),('cards','card_layer_height_mm')]:
        layer=pr[key];p=resolve(f'{layer:.2f}mm Standard @BBL P2S')
        p.update({'layer_height':str(layer),'initial_layer_print_height':str(pr['initial_layer_height_mm']),'wall_loops':str(pr['wall_loops']),'sparse_infill_density':str(pr['infill_percent'])+'%','sparse_infill_pattern':pr['infill_pattern'],'top_shell_layers':str(pr['top_shell_layers']),'bottom_shell_layers':str(pr['bottom_shell_layers']),'xy_contour_compensation':str(pr['xy_contour_compensation_mm'] if kind=='cards' else 0),'elefant_foot_compensation':str(pr['elephant_foot_compensation_mm']),'brim_type':'outer_only','brim_width':str(pr['brim_width_mm']),'skirt_loops':str(pr['skirt_loops']),'enable_support':'1' if pr['support_enabled'] else '0','enable_prime_tower':'1' if pr['prime_tower_enabled'] else '0','flush_into_infill':'0','print_sequence':pr['print_sequence']})
        processes[kind]=p
    return machine,processes,filament


def write_project(path,items,colors,settings):
    mark_print_overrides(settings,len(colors))
    model=ET.Element(f'{{{CORE}}}model',{'unit':'millimeter',f'{{{PROD}}}requiredextensions':'p'})
    ET.SubElement(model,f'{{{CORE}}}metadata',name='Application').text='BambuStudio-02.06.00.51'
    ET.SubElement(model,f'{{{CORE}}}metadata',name='BambuStudio:3mfVersion').text='1'
    resources=ET.SubElement(model,f'{{{CORE}}}resources'); build=ET.SubElement(model,f'{{{CORE}}}build')
    cfg=ET.Element('config');plate=ET.SubElement(cfg,'plate')
    def meta(e,k,v):ET.SubElement(e,'metadata',key=k,value=str(v))
    meta(plate,'plater_id',1);meta(plate,'plater_name',path.stem);meta(plate,'locked','false');meta(plate,'filament_map_mode','Auto For Flush')
    idx=0
    for item in items:
        partids=[]
        for name,color,m in item['parts']:
            idx+=1;pid=idx;partids.append((pid,name,color,m))
            obj=ET.SubElement(resources,f'{{{CORE}}}object',id=str(pid),type='model');mesh=ET.SubElement(obj,f'{{{CORE}}}mesh');vs=ET.SubElement(mesh,f'{{{CORE}}}vertices');fs=ET.SubElement(mesh,f'{{{CORE}}}triangles')
            for x,y,z in m.vertices:ET.SubElement(vs,f'{{{CORE}}}vertex',x=f'{x:.9f}',y=f'{y:.9f}',z=f'{z:.9f}')
            for a,b,c in m.faces:ET.SubElement(fs,f'{{{CORE}}}triangle',v1=str(a),v2=str(b),v3=str(c))
        idx+=1;oid=idx;obj=ET.SubElement(resources,f'{{{CORE}}}object',id=str(oid),type='model');comp=ET.SubElement(obj,f'{{{CORE}}}components')
        for pid,*_ in partids:ET.SubElement(comp,f'{{{CORE}}}component',objectid=str(pid))
        rot='0 1 0 -1 0 0 0 0 1' if item['rotate'] else '1 0 0 0 1 0 0 0 1'
        ET.SubElement(build,f'{{{CORE}}}item',objectid=str(oid),transform=f"{rot} {item['x']} {item['y']} 0",printable='1')
        oc=ET.SubElement(cfg,'object',id=str(oid));meta(oc,'name',item['name']);meta(oc,'extruder',colors.index(partids[0][2])+1)
        object_settings={k:settings[k] for k in OBJECT_LIGHTWEIGHT_KEYS}
        object_settings.update(item.get('settings',{}))
        for k,v in object_settings.items():meta(oc,k,v)
        for pid,name,color,m in partids:
            pc=ET.SubElement(oc,'part',id=str(pid),subtype='normal_part');meta(pc,'name',name);meta(pc,'extruder',colors.index(color)+1);meta(pc,'matrix','1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1')
            ET.SubElement(pc,'mesh_stat',face_count=str(len(m.faces)),edges_fixed='0',degenerate_facets='0',facets_removed='0',facets_reversed='0',backwards_edges='0')
        mi=ET.SubElement(plate,'model_instance');meta(mi,'object_id',oid);meta(mi,'instance_id',0);meta(mi,'identify_id',oid+100)
    ET.SubElement(cfg,'assemble')
    ct='<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>'
    rel='<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>'
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml',ct);z.writestr('_rels/.rels',rel);z.writestr('3D/3dmodel.model',ET.tostring(model,encoding='utf-8',xml_declaration=True));z.writestr('Metadata/model_settings.config',ET.tostring(cfg,encoding='utf-8',xml_declaration=True));z.writestr('Metadata/project_settings.config',json.dumps(settings,ensure_ascii=False))


def main():
    OUT.mkdir(exist_ok=True);config=json.loads((ROOT/'model.json').read_text());pr=config['printing'];palette={c['id']:c for c in pr['colors']}
    nodes=[n for n in config['nodes'] if n.get('params',{}).get('group') in ['terrain','tray']]
    cards=[n for n in nodes if n['params']['group']=='terrain'];colors,edges=coloring(config,cards)
    machine,processes,filament=resolved_profiles(config)
    for color in pr['colors']:
        preset=copy.deepcopy(filament);preset['filament_colour']=[color['hex']]
        prepare.write_json(OUT/f"filament_color_{color['id']}.json",preset)
    jobs=[];base_report=None;base_reports={}
    for n in nodes:
        if n['params']['group']!='tray':continue
        if n['name'] in pr['sea_color_base_objects']:
            parts,detail=color_base(config,n);base_reports[n['name']]=detail
            if n['name']==pr['multicolor_base_object']:base_report=detail
        else:
            m=mesh_for(n);offset=(m.bounds[0]+m.bounds[1])/2;offset[2]=m.bounds[0,2];m.vertices-=offset;parts=[(n['name'],pr['base_filament_id'],m)]
        jobs.append(('base',n['name'],[{'name':n['name'],'parts':parts,'x':config['constants']['PRINT_BED']*5,'y':config['constants']['PRINT_BED']*5,'rotate':False,'bbox':None}]))
    for color in pr['province_filament_ids']:
        items=[]
        for n in cards:
            if colors[n['params']['code']]!=color:continue
            m=mesh_for(n);offset=(m.bounds[0]+m.bounds[1])/2;offset[2]=m.bounds[0,2];m.vertices-=offset
            items.append((str(n['params']['code'])+'_'+n['params']['province'],[(n['name'],color,m)]))
        for i,b in enumerate(pack(items,config),1):jobs.append(('cards',f'Provinces_Color{color}_{i:02}',b['items']))
    report={'palette':pr['colors'],'province_colors':{str(n['params']['code']):{'name':n['params']['province'],'filament_id':colors[n['params']['code']]} for n in cards},'adjacency_edges':edges,'multicolor_base':base_report,'multicolor_bases':base_reports,'plates':[]}
    # Probe export contains validated, resolved official machine and filament defaults.
    template=json.loads((OUT/'cli_profile_probe.json').read_text())
    for num,(kind,title,items) in enumerate(jobs,1):
        used=sorted({color for item in items for _,color,_ in item['parts']})
        settings=copy.deepcopy(template);settings.update(machine);settings.update(processes[kind]);settings['curr_bed_type']=pr['bed_type']
        for key,value in filament.items():
            if isinstance(value,list):settings[key]=[value[0] for _ in used] if len(value)==1 else value
            elif key not in ['type','name','from','instantiation','setting_id']:settings[key]=value
        variant_count=len(filament['filament_extruder_variant'])
        for key in FILAMENT_VARIANT_KEYS:
            value=filament.get(key,template.get(key))
            if isinstance(value,list):
                if len(value)==1:value=value*variant_count
                assert len(value)==variant_count,(key,value)
                settings[key]=value*len(used)
        settings['filament_self_index']=[str(i+1) for i in range(len(used)) for _ in range(variant_count)]
        settings['filament_map']=['1']*len(used)
        settings['filament_nozzle_map']=['1']*len(used)
        settings['filament_volume_map']=['0']*len(used)
        settings['filament_colour']=[palette[i]['hex'] for i in used];settings['filament_settings_id']=[pr['material']]*len(used)
        settings['filament_ids']=['GFA00']*len(used);settings['filament_is_support']=['0']*len(used)
        settings['flush_volumes_matrix']=['0' if i==j else '280' for i in range(len(used)) for j in range(len(used))];settings['flush_volumes_vector']=['140']*(len(used)*2)
        settings['flush_multiplier']=['1']
        settings['printer_settings_id']=pr['printer']
        settings['print_settings_id']=processes[kind]['name']
        settings['print_compatible_printers']=[pr['printer']]
        settings['filament_compatible_printers']=[pr['printer']]
        settings.pop('compatible_printers',None)
        if title==pr['multicolor_base_object']:
            settings['wall_generator']=pr['multicolor_wall_generator']
            settings['min_bead_width']=str(pr['multicolor_min_bead_width_percent'])+'%'
        filename=f'{num:02}_{title}.3mf';write_project(OUT/filename,items,used,settings)
        report['plates'].append({'number':num,'file':filename,'kind':kind,'global_filament_ids':used,'local_filament_colors':[palette[i]['name'] for i in used],'objects':[item['name'] for item in items],'object_bboxes_mm':[item['bbox'] for item in items],'layer_height_mm':float(settings['layer_height'])})
    # A small fit coupon uses the full Beijing card and its actual contour.
    trial_node=next(n for n in cards if n['params']['code']==pr['fit_test_province_code'])
    trial_card=mesh_for(trial_node);center=(trial_card.bounds[0]+trial_card.bounds[1])/2
    outlines=json.loads((ROOT/'data/processed/province_print_outlines.geojson').read_text())['features']
    contour=shape(next(f['geometry'] for f in outlines if int(f['properties']['code'])==pr['fit_test_province_code']))
    cx,cy=center[:2]/10;w=pr['fit_test_board_width_mm']/20;h=pr['fit_test_board_height_mm']/20
    trial_slot=contour.buffer(config['constants']['SLOT_CLEARANCE'],quad_segs=24,join_style='round')
    trial_board=prepare.make_tray(box(cx-w,cy-h,cx+w,cy+h),trial_slot,config['constants']);trial_board.vertices*=10;trial_board.vertices[:,:2]-=center[:2]
    trial_card.vertices[:,:2]-=center[:2];trial_card.vertices[:,2]-=trial_card.bounds[0,2]
    color=colors[pr['fit_test_province_code']]
    trial_items=pack([(f"北京试配底座_{config['constants']['SLOT_DEPTH']*10:g}mm槽_每侧{config['constants']['SLOT_CLEARANCE']*10:g}mm公差",[('北京试配底座',color,trial_board)]),('北京省形试配插板',[('北京省形试配插板',color,trial_card)])],config)[0]['items']
    next(i for i in trial_items if i['name'].startswith('北京试配底座'))['settings']={'xy_contour_compensation':'0'}
    with zipfile.ZipFile(OUT/report['plates'][4]['file']) as z:trial_settings=json.loads(z.read('Metadata/project_settings.config'))
    trial_settings['filament_colour']=[palette[color]['hex']]
    filename='00_Fit_Test_Beijing.3mf';write_project(OUT/filename,trial_items,[color],trial_settings)
    report['plates'].insert(0,{'number':0,'file':filename,'kind':'cards','role':'fit_test','global_filament_ids':[color],'local_filament_colors':[palette[color]['name']],'objects':[i['name'] for i in trial_items],'object_bboxes_mm':[],'layer_height_mm':pr['card_layer_height_mm']})
    prepare.write_json(OUT/'print_manifest.json',report)
    print(f"Prepared {len(jobs)} production plates + 1 fit-test plate; 32 cards, four bases, six colors; base partition {base_report}")

if __name__=='__main__':main()
