"""Independently read binary STL; check units, closed edges and orientation.

Usage: python3 tools/check_stl.py file.stl --size-mm X Y Z --report report.json
"""
import argparse
from collections import Counter
import json
import math
from pathlib import Path
import struct


def check(path, expected, tolerance=.02):
    data=Path(path).read_bytes()
    count=struct.unpack_from("<I",data,80)[0]
    assert len(data)==84+count*50,"Binary STL record length mismatch"
    edges=Counter();directed=Counter();lo=[math.inf]*3;hi=[-math.inf]*3
    degenerate=0;volume=0
    for i in range(count):
        row=struct.unpack_from("<12fH",data,84+i*50)
        vertices=[tuple(row[k:k+3]) for k in (3,6,9)]
        a,b,c=vertices
        u=[b[j]-a[j] for j in range(3)];v=[c[j]-a[j] for j in range(3)]
        cross=(u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0])
        degenerate+=sum(x*x for x in cross)==0
        volume+=sum(a[j]*cross[j] for j in range(3))/6
        for vertex in vertices:
            for j,x in enumerate(vertex):
                assert math.isfinite(x),"Nonfinite STL coordinate"
                lo[j]=min(lo[j],x);hi[j]=max(hi[j],x)
        for a,b in zip(vertices,vertices[1:]+vertices[:1]):
            edges[tuple(sorted((a,b)))]+=1;directed[(a,b)]+=1
    bad=sum(n!=2 for n in edges.values())
    orientation=sum(directed[(a,b)]!=directed[(b,a)] for a,b in edges)
    parents={v:v for edge in edges for v in edge}
    def root(v):
        while parents[v]!=v:
            parents[v]=parents[parents[v]];v=parents[v]
        return v
    for a,b in edges:
        ra=root(a);rb=root(b)
        if ra!=rb:parents[ra]=rb
    components=len({root(v) for v in parents})
    size=[b-a for a,b in zip(lo,hi)]
    assert degenerate==bad==orientation==0,(degenerate,bad,orientation)
    assert components==1,components
    assert volume>0,volume
    assert all(abs(a-b)<tolerance for a,b in zip(size,expected)),(size,expected)
    return {"file":Path(path).name,"units":"mm","triangles":count,"bbox_mm":size,"expected_bbox_mm":expected,"connected_components":components,"degenerate_triangles":degenerate,"edges_not_shared_twice":bad,"inconsistent_edge_orientation":orientation,"volume_mm3":volume,"tolerance_mm":tolerance}


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file");parser.add_argument("--size-mm",type=float,nargs=3,required=True)
    parser.add_argument("--report")
    args=parser.parse_args();report=check(args.file,args.size_mm)
    if args.report:Path(args.report).write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report))
