"""Independent closed-volume, palette and assembly validation of the AMS 3MF."""
import argparse
from collections import Counter
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile


def check(path,source_report):
    ns={'m':'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}
    with zipfile.ZipFile(path) as z:
        model=ET.fromstring(z.read('3D/3dmodel.model'))
        config=ET.fromstring(z.read('Metadata/model_settings.config'))
        settings=json.loads(z.read('Metadata/project_settings.config'))
    assert model.attrib['unit']=='millimeter'
    objs={o.attrib['id']:o for o in model.findall('m:resources/m:object',ns)}
    builds=model.findall('m:build/m:item',ns);assert len(builds)==1
    assembly=objs[builds[0].attrib['objectid']]
    components=assembly.findall('m:components/m:component',ns);assert len(components)==4
    cfg=config.find('object');assert cfg.attrib['id']==assembly.attrib['id']
    assignments={p.attrib['id']: {m.attrib['key']:m.attrib['value'] for m in p.findall('metadata')} for p in cfg.findall('part')}
    colors=settings['filament_colour'];assert len(set(colors))==4
    lo=[math.inf]*3;hi=[-math.inf]*3;reports=[]
    for index,component in enumerate(components,1):
        node=objs[component.attrib['objectid']];mesh=node.find('m:mesh',ns)
        vertices=[tuple(float(v.attrib[k]) for k in ('x','y','z')) for v in mesh.findall('m:vertices/m:vertex',ns)]
        edges=Counter();directed=Counter();degenerate=0;volume=0
        triangles=mesh.findall('m:triangles/m:triangle',ns)
        for tri in triangles:
            a,b,c=(vertices[int(tri.attrib[k])] for k in ('v1','v2','v3'))
            u=[b[k]-a[k] for k in range(3)];v=[c[k]-a[k] for k in range(3)]
            cross=(u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0])
            degenerate+=sum(x*x for x in cross)==0
            volume+=sum(a[k]*cross[k] for k in range(3))/6
            for point in (a,b,c):
                for k,x in enumerate(point):
                    assert math.isfinite(x)
                    lo[k]=min(lo[k],x);hi[k]=max(hi[k],x)
            for x,y in ((a,b),(b,c),(c,a)):
                edges[tuple(sorted((x,y)))]+=1;directed[(x,y)]+=1
        bad=sum(v!=2 for v in edges.values())
        flipped=sum(directed[(a,b)]!=directed[(b,a)] for a,b in edges)
        assert degenerate==bad==flipped==0,(node.attrib['name'],degenerate,bad,flipped)
        assert volume>0
        parent={v:v for edge in edges for v in edge}
        def root(v):
            while parent[v]!=v:parent[v]=parent[parent[v]];v=parent[v]
            return v
        for a,b in edges:
            a=root(a);b=root(b)
            if a!=b:parent[a]=b
        count=len({root(v) for v in parent})
        assert count==(4 if index==3 else 1),(node.attrib['name'],count)
        assigned=assignments[node.attrib['id']]
        assert int(assigned['extruder'])==index
        reports.append({'name':node.attrib['name'],'extruder':index,'color':colors[index-1],'triangles':len(triangles),'connected_components':count,'degenerate_triangles':degenerate,'edges_not_shared_twice':bad,'inconsistent_edge_orientation':flipped,'volume_mm3':volume})
    size=[b-a for a,b in zip(lo,hi)]
    source=json.loads(Path(source_report).read_text())
    difference=abs(sum(r['volume_mm3'] for r in reports)-source['source_volume_cm3']*1000)
    assert difference<.1,difference
    assert all(abs(a-b*10)<.02 for a,b in zip(size,source['assembly_dimensions_cm'])),size
    return {'file':Path(path).name,'units':'mm','assembly_count':1,'material_volumes':reports,'bbox_mm':size,'partition_volume_error_mm3':difference,'build_transform':builds[0].attrib['transform'],'sliced':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('file');parser.add_argument('--source-report',required=True);parser.add_argument('--report',required=True)
    args=parser.parse_args();report=check(args.file,args.source_report)
    Path(args.report).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False))
