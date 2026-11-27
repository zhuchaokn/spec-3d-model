"""Round-trip check every actual mesh in a Bambu 3MF archive."""
import argparse,zipfile,xml.etree.ElementTree as ET
import numpy as np,trimesh
C='{http://schemas.microsoft.com/3dmanufacturing/core/2015/02}'


def verify(path):
    count=0
    with zipfile.ZipFile(path) as archive:
        for name in archive.namelist():
            if not name.endswith('.model'):continue
            root=ET.fromstring(archive.read(name))
            for obj in root.findall(C+'resources/'+C+'object'):
                mesh=obj.find(C+'mesh')
                if mesh is None:continue
                vertices=np.array([[float(v.get(k)) for k in ['x','y','z']] for v in mesh.findall(C+'vertices/'+C+'vertex')])
                faces=np.array([[int(f.get(k)) for k in ['v1','v2','v3']] for f in mesh.findall(C+'triangles/'+C+'triangle')])
                solid=trimesh.Trimesh(vertices=vertices,faces=faces,process=True)
                assert solid.is_watertight and solid.is_winding_consistent and solid.volume>0,(name,obj.get('id'))
                count+=1
    return count


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('archive');args=parser.parse_args()
    print('Verified closed 3MF meshes:',verify(args.archive))
