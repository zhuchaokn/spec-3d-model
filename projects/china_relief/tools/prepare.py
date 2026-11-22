"""Acquire auditable terrain data and prepare closed meshes; never imports bpy.

All project dimensions come from model.json. Derived meshes can be regenerated.
Run: .venv/bin/python tools/prepare.py
"""
import concurrent.futures
import hashlib
import json
import math
from pathlib import Path
import time

import numpy as np
import requests
import rasterio
from rasterio.merge import merge
from scipy.ndimage import map_coordinates
from pyproj import Transformer
import shapely
from shapely.geometry import Polygon, MultiPolygon, Point, box, shape, mapping
from shapely.ops import transform, unary_union
from shapely.affinity import translate
import triangle
import trimesh
import inset

PROJ = Path(__file__).resolve().parents[1]
MODEL = PROJ / 'model.json'
RAW = PROJ / 'data/raw'
OUT = PROJ / 'data/processed'


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def polygons(g):
    if g.is_empty:
        return []
    if isinstance(g, Polygon):
        return [g]
    if isinstance(g, MultiPolygon):
        return list(g.geoms)
    return [p for child in getattr(g, 'geoms', []) for p in polygons(child)]


def gcj_forward(lon, lat):
    """Standard candidate GCJ-02 offset, vectorized; its use is recorded explicitly."""
    lon, lat = np.asarray(lon), np.asarray(lat)
    x, y = lon - 105, lat - 35
    dl = -100 + 2*x + 3*y + .2*y*y + .1*x*y + .2*np.sqrt(np.abs(x))
    dn = 300 + x + 2*y + .1*x*x + .1*x*y + .1*np.sqrt(np.abs(x))
    common = (20*np.sin(6*x*np.pi) + 20*np.sin(2*x*np.pi))*2/3
    dl += common + (20*np.sin(y*np.pi) + 40*np.sin(y*np.pi/3))*2/3
    dl += (160*np.sin(y*np.pi/12) + 320*np.sin(y*np.pi/30))*2/3
    dn += common + (20*np.sin(x*np.pi) + 40*np.sin(x*np.pi/3))*2/3
    dn += (150*np.sin(x*np.pi/12) + 300*np.sin(x*np.pi/30))*2/3
    rad = np.radians(lat)
    magic = 1 - .006693421622965943*np.sin(rad)**2
    dl = dl*180 / ((6378245*(1-.006693421622965943))/(magic*np.sqrt(magic))*np.pi)
    dn = dn*180 / (6378245/np.sqrt(magic)*np.cos(rad)*np.pi)
    inside = (lon >= 72.004) & (lon <= 137.8347) & (lat >= .8293) & (lat <= 55.8271)
    return lon + np.where(inside, dn, 0), lat + np.where(inside, dl, 0)


def gcj_inverse(lon, lat, z=None):
    origlon, origlat = np.asarray(lon,dtype=float), np.asarray(lat,dtype=float)
    wlon, wlat = origlon.copy(), origlat.copy()
    for _ in range(8):
        flon, flat = gcj_forward(wlon, wlat)
        wlon -= flon - origlon
        wlat -= flat - origlat
    return wlon, wlat


def get_provinces(config):
    data = json.loads((PROJ / config['data']['boundary']).read_text())
    provinces, repairs = [], []
    for f in data['features']:
        code = f['properties'].get('adcode')
        if not isinstance(code, int):
            continue  # 100000_JD is a cartographic dashed line, not land.
        g = shape(f['geometry'])
        if not g.is_valid:
            repairs.append({'code': code, 'reason': shapely.is_valid_reason(g)})
            g = shapely.make_valid(g)
            g = unary_union(polygons(g))
        g = transform(gcj_inverse, g)
        provinces.append({'code': code, 'name': f['properties']['name'], 'wgs': g})
    assert len(provinces) == 34 and len({p['code'] for p in provinces}) == 34
    return sorted(provinces, key=lambda p: p['code']), repairs


def tile_lonlat(z, x, y):
    n = 2**z
    lon0, lon1 = x/n*360-180, (x+1)/n*360-180
    lat1 = math.degrees(math.atan(math.sinh(math.pi*(1-2*y/n))))
    lat0 = math.degrees(math.atan(math.sinh(math.pi*(1-2*(y+1)/n))))
    return box(lon0, lat0, lon1, lat1)


def acquire_terrain(config, land):
    z = int(config['constants']['TERRAIN_ZOOM'])
    buffered = land.buffer(.05)  # Border pixels need neighboring tiles for bilinear interpolation.
    tiles = [(x,y) for x in range(2**z) for y in range(2**z)
             if buffered.intersects(tile_lonlat(z, x, y))]
    folder = RAW / 'terrain_tiles'
    folder.mkdir(exist_ok=True)
    print(f'Terrain: {len(tiles)} intersecting land tiles at zoom {z}', flush=True)

    def download(xy):
        x,y = xy
        path = folder / f'{z}_{x}_{y}.tif'
        url = config['data']['terrain_url'].format(z=z, x=x, y=y)
        source = None
        if not path.exists():
            for attempt in range(3):
                try:
                    response = requests.get(url, timeout=(15, 60))
                    response.raise_for_status()
                    source = response.headers.get('x-amz-meta-x-imagery-sources')
                    tmp = path.with_suffix('.part')
                    tmp.write_bytes(response.content)
                    with rasterio.open(tmp) as ds:
                        assert ds.crs and ds.count == 1
                    tmp.replace(path)
                    path.with_suffix('.source.json').write_text(json.dumps({'source': source}))
                    break
                except Exception:
                    if attempt == 2:
                        raise
                    time.sleep(1 + attempt)
        meta = path.with_suffix('.source.json')
        if meta.exists():
            source = json.loads(meta.read_text()).get('source')
        with rasterio.open(path) as ds:
            entry = {'url': url, 'file': str(path.relative_to(PROJ)), 'sha256': sha(path),
                     'source': source, 'crs': str(ds.crs), 'pixel_size_m': list(ds.res),
                     'shape': list(ds.shape), 'nodata': ds.nodata}
        return path, entry

    entries = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        futures = [pool.submit(download, xy) for xy in tiles]
        for index, future in enumerate(concurrent.futures.as_completed(futures), 1):
            entries.append(future.result())
            if index % 10 == 0 or index == len(tiles):
                print(f'  terrain downloaded/checked {index}/{len(tiles)}', flush=True)
    entries.sort(key=lambda item: item[1]['file'])
    write_json(RAW / 'terrain_manifest.json', [e for _, e in entries])
    datasets = [rasterio.open(p) for p, _ in entries]
    try:
        array, affine = merge(datasets, nodata=np.nan, dtype='float32')
        profile = datasets[0].profile.copy()
        profile.update(height=array.shape[1], width=array.shape[2], transform=affine,
                       dtype='float32', nodata=np.nan, compress='deflate')
        with rasterio.open(OUT / 'terrain_mosaic.tif', 'w', **profile) as dest:
            dest.write(array)
    finally:
        for ds in datasets:
            ds.close()
    return array[0], affine, entries


def dense_ring(coords, spacing):
    result = []
    for a, b in zip(coords[:-1], coords[1:]):
        a, b = np.array(a[:2]), np.array(b[:2])
        n = max(1, math.ceil(np.linalg.norm(b-a)/spacing))
        result.extend(a + (b-a)*j/n for j in range(n))
    return np.asarray(result)


def triangulate(poly, spacing=None, grid=False):
    components=polygons(poly)
    if len(components)>1:
        vs=[]; fs=[]; count=0
        for component in components:
            v,f=triangulate(component,spacing=spacing,grid=grid)
            vs.append(v); fs.append(f+count); count+=len(v)
        return np.concatenate(vs),np.concatenate(fs)
    vertices, segments, holes = [], [], []
    for p in polygons(poly):
        for index, ring in enumerate([p.exterior, *p.interiors]):
            pts = np.array(ring.coords[:-1])
            start = len(vertices)
            vertices.extend(pts)
            segments.extend((start+i, start+(i+1)%len(pts)) for i in range(len(pts)))
            if index:
                holes.append(list(Polygon(ring).representative_point().coords)[0])
        if grid:
            x0,y0,x1,y1 = p.bounds
            xs = np.arange(math.ceil(x0/spacing)*spacing, x1, spacing)
            ys = np.arange(math.ceil(y0/spacing)*spacing, y1, spacing)
            xx,yy = np.meshgrid(xs,ys)
            keep = shapely.contains_xy(p, xx.ravel(), yy.ravel())
            candidates = np.column_stack((xx.ravel()[keep], yy.ravel()[keep]))
            # Avoid coincident input vertices and points exactly on boundary segments.
            if len(candidates):
                distances = shapely.distance(shapely.points(candidates), p.boundary)
                vertices.extend(candidates[distances > 1e-8])
    raw_vertices=np.asarray(vertices)
    unique_vertices,inverse=np.unique(raw_vertices,axis=0,return_inverse=True)
    edges=inverse[np.asarray(segments)]
    edges=edges[edges[:,0]!=edges[:,1]]
    edges=np.unique(np.sort(edges,axis=1),axis=0)
    spec = {'vertices': unique_vertices, 'segments': edges}
    if holes:
        spec['holes'] = np.asarray(holes)
    result = triangle.triangulate(spec, 'pQ')
    v, f = result['vertices'], result['triangles']
    edge_a=v[f[:,1]]-v[f[:,0]]; edge_b=v[f[:,2]]-v[f[:,0]]
    cross = edge_a[:,0]*edge_b[:,1]-edge_a[:,1]*edge_b[:,0]
    if np.any(cross == 0):
        raise ValueError('Degenerate triangulation')
    f[cross < 0] = f[cross < 0][:, [0,2,1]]
    return v, f


def build_solid(poly, sampler, bottom_z, c):
    """Flat-bottom removable terrain card; no locating pins or bottom sockets."""
    spacing = c['MESH_SPACING']
    # Densify the actual polygon once so top and bottom have identical outer segments.
    p = Polygon(dense_ring(list(poly.exterior.coords), spacing),
                [dense_ring(list(r.coords), spacing) for r in poly.interiors])
    top_v, top_f = triangulate(p, grid=True, spacing=spacing)
    bottom_v, bottom_f = triangulate(p)
    h = sampler(top_v)
    top_z = bottom_z + c['TERRAIN_BASE'] + (h-c['ELEVATION_DATUM'])*c['HORIZONTAL_CM_PER_M']*c['VERTICAL_EXAGGERATION']
    if np.min(top_z-bottom_z) < c['TERRAIN_BASE']-1e-6:
        raise ValueError(f'Elevation falls below configured datum: {np.min(h)}')
    verts = list(np.column_stack((top_v,top_z))) + list(np.column_stack((bottom_v,np.full(len(bottom_v),bottom_z))))
    faces = list(top_f) + list(bottom_f[:,[0,2,1]]+len(top_v))

    def append_ring_walls(ring, zs, inward=False):
        pts = np.asarray(ring.coords[:-1])
        start = len(verts)
        low, high = zs
        if np.isscalar(high):
            high = np.full(len(pts), high)
        verts.extend(np.column_stack((pts,np.full(len(pts),low))))
        verts.extend(np.column_stack((pts,high)))
        n = len(pts)
        for i in range(n):
            j = (i+1)%n
            # Ring winding is handled explicitly; exterior is outward, interior inward.
            ccw = Polygon(ring).exterior.is_ccw
            want_ccw = not inward
            tri = [[start+n+i,start+i,start+j], [start+n+i,start+j,start+n+j]]
            if ccw != want_ccw:
                tri = [t[::-1] for t in tri]
            faces.extend(tri)

    for index, ring in enumerate([p.exterior,*p.interiors]):
        pts = np.asarray(ring.coords[:-1])
        z = bottom_z + c['TERRAIN_BASE'] + (sampler(pts)-c['ELEVATION_DATUM'])*c['HORIZONTAL_CM_PER_M']*c['VERTICAL_EXAGGERATION']
        append_ring_walls(ring, (bottom_z,z), inward=bool(index))
    mesh = trimesh.Trimesh(vertices=np.asarray(verts), faces=np.asarray(faces), process=False)
    mesh.merge_vertices(digits_vertex=8)
    if not mesh.is_watertight or not mesh.is_winding_consistent or mesh.volume <= 0:
        raise ValueError(f'Invalid solid: closed={mesh.is_watertight}, winding={mesh.is_winding_consistent}')
    return mesh, (float(np.min(h)), float(np.max(h)))


def make_tray(poly, wells, c, fixed_regions=None, sampler=None, raised_regions=None):
    """Single closed slab with province-shaped pockets, including pockets across tile seams.

    Build exposed floors, upper ledges and both levels of walls directly. The
    lower outer ring is noded at every pocket/outer-edge intersection so welding
    does not leave T-junctions. No overlapping solids or chained mesh booleans.
    """
    sources=[(fixed_regions if fixed_regions is not None else Polygon(),None)]+list(raised_regions or [])
    wells=unary_union([wells,*[g for g,z in sources]])
    pocket=poly.intersection(wells)
    ledge=poly.difference(wells)
    fixed=[]; fixed_levels=[]
    for source,level in sources:
        for p in polygons(source.intersection(pocket)):
            fixed.append(Polygon(dense_ring(list(p.exterior.coords),c['MESH_SPACING']),
                                 [dense_ring(list(r.coords),c['MESH_SPACING']) for r in p.interiors]) if level is None else p)
            fixed_levels.append(level)
    fixed_union=unary_union(fixed)
    exposed_floor=pocket.difference(fixed_union) if fixed else pocket
    verts=[]; faces=[]
    low=c['TRAY_FLOOR']; high=low+c['SLOT_DEPTH']

    def surface(region,z,reverse=False):
        if region.is_empty:return
        v,f=triangulate(region); start=len(verts)
        verts.extend(np.column_stack((v,np.full(len(v),z))))
        faces.extend((f[:,[0,2,1]] if reverse else f)+start)

    def walls(ring,z0,z1,inward=False,skip_boundary=None):
        pts=np.array(ring.coords[:-1]); start=len(verts); n=len(pts)
        verts.extend(np.column_stack((pts,np.full(n,z0))))
        verts.extend(np.column_stack((pts,np.full(n,z1))))
        reverse=Polygon(ring).exterior.is_ccw != (not inward)
        for i in range(n):
            j=(i+1)%n
            if skip_boundary is not None and not skip_boundary.is_empty:
                if Point((pts[i]+pts[j])/2).distance(skip_boundary)<1e-8:
                    continue
            pair=[[start+n+i,start+i,start+j],[start+n+i,start+j,start+n+j]]
            faces.extend([t[::-1] for t in pair] if reverse else pair)

    candidate=[]
    for region in [exposed_floor,ledge,*fixed]:
        for p in polygons(region):
            for ring in [p.exterior,*p.interiors]:candidate.extend(ring.coords[:-1])
    candidate=np.unique(np.asarray(candidate),axis=0)
    # All surfaces sharing an edge must use identical segments, including a
    # fixed island touching the recess rim at a single point.
    boundary_points=candidate

    def node_ring(ring):
        points=[]
        for aa,bb in zip(ring.coords[:-1],ring.coords[1:]):
            a,b=np.array(aa),np.array(bb); direction=b-a; length2=np.dot(direction,direction)
            if length2 < 1e-20:
                continue
            delta=boundary_points-a
            t=(delta[:,0]*direction[0]+delta[:,1]*direction[1])/length2
            distances=np.abs(delta[:,0]*direction[1]-delta[:,1]*direction[0])/math.sqrt(length2)
            keep=(t>=-1e-10)&(t<1-1e-10)&(distances<1e-8)
            pts=boundary_points[keep]; order=np.argsort(t[keep])
            if len(pts):points.extend(pts[order])
            else:points.append(a)
        return points

    def node_region(region):
        return unary_union([Polygon(node_ring(p.exterior),[node_ring(r) for r in p.interiors])
                            for p in polygons(region)])

    lower=Polygon(node_ring(poly.exterior),[node_ring(r) for r in poly.interiors])
    exposed_floor=node_region(exposed_floor)
    ledge=node_region(ledge)
    fixed=[node_region(p) for p in fixed]
    surface(lower,0,True)
    surface(exposed_floor,low)
    surface(ledge,high)
    for i,ring in enumerate([lower.exterior,*lower.interiors]):walls(ring,0,low,bool(i))
    for p in polygons(ledge):
        for i,ring in enumerate([p.exterior,*p.interiors]):
            walls(ring,low,high,bool(i),fixed_union.boundary)
    for p,level in zip(fixed,fixed_levels):
        v,f=triangulate(p,spacing=c['MESH_SPACING'],grid=level is None)
        heights=(low+c['TERRAIN_BASE']+(sampler(v)-c['ELEVATION_DATUM'])*c['HORIZONTAL_CM_PER_M']*c['VERTICAL_EXAGGERATION']
                 if level is None else np.full(len(v),level))
        if np.min(heights)<high:
            raise ValueError('Fixed terrain falls below surrounding slab surface')
        start=len(verts); verts.extend(np.column_stack((v,heights))); faces.extend(f+start)
        for inward,ring in enumerate([p.exterior,*p.interiors]):
            points=np.array(ring.coords[:-1]); n=len(points); start=len(verts)
            z=(low+c['TERRAIN_BASE']+(sampler(points)-c['ELEVATION_DATUM'])*c['HORIZONTAL_CM_PER_M']*c['VERTICAL_EXAGGERATION']
               if level is None else np.full(n,level))
            # The slab already occupies low..high along the outer coastline.
            # Only expose this lower wall where a fixed detail faces a card
            # recess; upper walls join the surrounding slab at high directly.
            walls(ring,low,high,bool(inward),ledge.boundary)
            start=len(verts)
            verts.extend(np.column_stack((points,np.full(n,high))))
            verts.extend(np.column_stack((points,z)))
            reverse=Polygon(ring).exterior.is_ccw != (not bool(inward))
            for i in range(n):
                j=(i+1)%n
                pair=[[start+n+i,start+i,start+j],[start+n+i,start+j,start+n+j]]
                faces.extend([t[::-1] for t in pair] if reverse else pair)
    mesh=trimesh.Trimesh(vertices=np.asarray(verts),faces=np.asarray(faces),process=False)
    mesh.merge_vertices(digits_vertex=8)
    # Coincident frame/partition vertices can collapse an infinitesimal input
    # triangle during welding. Remove only zero-area faces, keeping thin detail.
    face_count=len(mesh.faces)
    mesh.update_faces(mesh.nondegenerate_faces(height=0))
    mesh.metadata['zero_area_faces_removed']=face_count-len(mesh.faces)
    if not mesh.is_watertight or not mesh.is_winding_consistent or mesh.volume<=0:
        np.savez_compressed(OUT/'invalid_tray.npz',vertices=mesh.vertices,faces=mesh.faces)
        write_json(OUT/'invalid_tray_geometry.json',{'outline':mapping(poly),'pocket':mapping(pocket),'fixed':mapping(fixed_union)})
        raise ValueError(f'Invalid pocket tray: closed={mesh.is_watertight}, winding={mesh.is_winding_consistent}')
    return mesh


def paddle_profile(c, socket=False):
    """Local +X circular head, broad neck, and smooth concave root joins."""
    length=c['TRAY_TAB_LENGTH'];width=c['TRAY_TAB_WIDTH'];head=c['TRAY_TAB_HEAD_WIDTH']
    r=head/2;blend=c['TRAY_PADDLE_BLEND_RADIUS'];segments=c['TRAY_PADDLE_QUAD_SEGMENTS']
    assert length>=head and width<head and blend<width/2
    circle=Point(length-r,0).buffer(r,quad_segs=segments)
    base=box(-3*blend,-head,0,head)
    neck=box(-3*blend,-width/2,length-r,width/2)
    # Closing rounds only the concave transitions. The circular head already
    # has its own radius; the virtual backing plate gives the root a fillet.
    profile=base.union(neck).union(circle).buffer(blend,quad_segs=segments).buffer(-blend,quad_segs=segments)
    # Discard micron-scale offset remnants on the virtual backing edge;
    # restore a short backing cap below the real plate edge for solid union.
    cut=c['NUMERICAL_GAP']
    profile=profile.intersection(box(cut,-head,length+head,head)).buffer(0)
    root=[v for u,v in profile.exterior.coords if abs(u-cut)<1e-10]
    assert root
    profile=profile.union(box(-c['TRAY_JOINT_OVERLAP'],min(root),cut,max(root)))
    if socket:profile=profile.intersection(box(0,-head,length+head,head)).buffer(0)
    return profile


def tray_polygon(cell, ix, iy, nx, ny, c):
    x0,y0,x1,y1=cell.bounds
    dovetail=bool(c.get('TRAY_DOVETAIL_ENABLED',0))
    seam=c.get('TRAY_SEAM_GAP',0) if dovetail else 0
    result=box(x0+(seam if ix else 0),y0+(seam if iy else 0),x1,y1)
    length,width,clear=c['TRAY_TAB_LENGTH'],c['TRAY_TAB_WIDTH'],c['TRAY_TAB_CLEARANCE']
    for fraction in [1/3,2/3]:
        y=y0+(y1-y0)*fraction
        x=x0+(x1-x0)*fraction
        if dovetail:
            head=c['TRAY_TAB_HEAD_WIDTH'];overlap=c['TRAY_JOINT_OVERLAP']
            def joint(cx,cy,vertical,socket=False):
                if c.get('TRAY_PADDLE_ENABLED'):
                    profile=paddle_profile(c,socket)
                    if vertical:profile=transform(lambda u,v:(v,u),profile)
                    return translate(profile,cx,cy)
                pts=[(-overlap,-width/2),(0,-width/2),(length,-head/2),(length,head/2),(0,width/2),(-overlap,width/2)]
                return Polygon([(cx+v,cy+u) if vertical else (cx+u,cy+v) for u,v in pts])
            if ix<nx-1:result=result.union(joint(x1,y,False))
            if iy<ny-1:result=result.union(joint(x,y1,True))
            style=1 if c.get('TRAY_PADDLE_ENABLED') else 2
            segments=c.get('TRAY_PADDLE_QUAD_SEGMENTS',16)
            if ix>0:result=result.difference(joint(x0,y,False,True).buffer(clear,join_style=style,quad_segs=segments))
            if iy>0:result=result.difference(joint(x,y0,True,True).buffer(clear,join_style=style,quad_segs=segments))
            continue
        if ix<nx-1:
            result=result.union(box(x1-.01,y-width/2,x1+length,y+width/2))
        if iy<ny-1:
            result=result.union(box(x-width/2,y1-.01,x+width/2,y1+length))
        if ix>0:
            result=result.difference(box(x0-.01,y-width/2-clear,x0+length+clear,y+width/2+clear))
        if iy>0:
            result=result.difference(box(x-width/2-clear,y0-.01,x+width/2+clear,y0+length+clear))
    # Round only the assembled board's external corners; retain all seams/tabs.
    radius=c.get('TRAY_OUTER_CORNER_RADIUS',0)
    if radius:
        for outer_x,cx in [(ix==0,x0),(ix==nx-1,x1)]:
            for outer_y,cy in [(iy==0,y0),(iy==ny-1,y1)]:
                if not (outer_x and outer_y):continue
                sx=1 if cx==x0 else -1;sy=1 if cy==y0 else -1
                center=Point(cx+sx*radius,cy+sy*radius)
                square=box(min(cx,cx+sx*radius),min(cy,cy+sy*radius),
                           max(cx,cx+sx*radius),max(cy,cy+sy*radius))
                result=result.difference(square.difference(center.buffer(radius,quad_segs=c['TRAY_CORNER_QUAD_SEGMENTS'])))
    return result


def store_mesh(name, mesh, params, offset, nodes):
    mm=trimesh.Trimesh(vertices=mesh.vertices*10,faces=mesh.faces,process=True)
    if not mm.is_watertight or not mm.is_winding_consistent:
        raise ValueError(f'Millimetre vertex welding exposes a contact/nonmanifold: {name}')
    local = mesh.vertices - np.array(offset)
    path=OUT/f'{name}.npz'
    np.savez_compressed(path, vertices=local.astype('float64'), faces=mesh.faces.astype('int32'))
    nodes.append({'name': name, 'op':'ops/mesh.py','offset': list(offset),
                  'params': dict(params, mesh_file=str(path.relative_to(PROJ)))})
    return {'object':name,'file':str(path.relative_to(PROJ)),
            'group':params['group'],
            'sha256':sha(path),'vertices':len(mesh.vertices),'triangles':len(mesh.faces),
            'dimensions_mm':list(mesh.extents*10), 'volume_mm3':float(mesh.volume*1000),
            'bounds_mm':(mesh.bounds*10).tolist(),
            'watertight':bool(mesh.is_watertight),'winding_consistent':bool(mesh.is_winding_consistent),
            'zero_area_faces_removed':mesh.metadata.get('zero_area_faces_removed',0),
            'connected_components':len(mesh.split(only_watertight=False))}


def main():
    config=json.loads(MODEL.read_text()); c=config['constants']; OUT.mkdir(exist_ok=True)
    provinces,repairs=get_provinces(config)
    original_count=sum(len(polygons(p['wgs'])) for p in provinces)
    omitted=[]
    # Nansha is omitted as a group; Xisha and other retained geometry remain data-driven.
    for p in provinces:
        kept=[]
        for part in polygons(p['wgs']):
            if p['code']==460000 and part.bounds[3]<c['NANSHA_MAX_LAT']:
                omitted.append({'type':'Feature','properties':{'code':p['code'],'reason':'Nansha moved to fixed inset; omitted only from main relief'},'geometry':mapping(part)})
            else:kept.append(part)
        p['wgs']=unary_union(kept)
    write_json(OUT/'omitted_nansha.geojson',{'type':'FeatureCollection','features':omitted})
    wgsland=unary_union([p['wgs'] for p in provinces])
    projection=Transformer.from_crs('EPSG:4326',config['data']['projection'],always_xy=True)
    projected=[transform(projection.transform,p['wgs']) for p in provinces]
    land=unary_union(projected); x0,y0,x1,y1=land.bounds
    factor=c['MAP_WIDTH']/(x1-x0); c['HORIZONTAL_CM_PER_M']=factor
    to_cm=lambda x,y,z=None: ((np.asarray(x)-(x0+x1)/2)*factor,(np.asarray(y)-y0)*factor)
    for p,g in zip(provinces,projected):p['cm']=transform(to_cm,g)
    overlaps=[]
    for i,p in enumerate(provinces):
        for q in provinces[i+1:]:
            area=p['cm'].intersection(q['cm']).area
            if area>1e-8:overlaps.append({'a':p['name'],'b':q['name'],'area_mm2':area*100})
    if sum(e['area_mm2'] for e in overlaps)>1:raise RuntimeError(f'Unexpected source overlap: {overlaps}')
    # Shared nominal borders: no inset, no province gap. Normalize the tiny source
    # overlaps once and snap shared vertices to a sub-nozzle numeric grid.
    occupied=Polygon(); normalizations=[]
    for p in provinces:
        original=p['cm']
        g=shapely.set_precision(original,c['NUMERICAL_GAP']/10)
        g=g.difference(occupied)
        if not g.is_valid:g=unary_union(polygons(shapely.make_valid(g)))
        occupied=occupied.union(g)
        g=g.simplify(c['NUMERICAL_GAP']/10,preserve_topology=True)
        normalizations.append({'code':p['code'],'changed_area_mm2':original.symmetric_difference(g).area*100})
        p['cm']=g
    landcm=unary_union([p['cm'] for p in provinces]); height=(y1-y0)*factor
    print(f'Map: {c["MAP_WIDTH"]*10:.1f} x {height*10:.1f} mm; no province gaps; {c["SLOT_DEPTH"]*10:g} mm shared recess',flush=True)
    array,affine,entries=acquire_terrain(config,wgsland)
    cm_to_m=Transformer.from_crs(config['data']['projection'],'EPSG:3857',always_xy=True)
    coastal_clamps=[0]; no_data=[0]

    def sample(points,count=False):
        points=np.asarray(points)
        mx=points[:,0]/factor+(x0+x1)/2; my=points[:,1]/factor+y0
        tx,ty=cm_to_m.transform(mx,my)
        cols=(np.asarray(tx)-affine.c)/affine.a-.5; rows=(np.asarray(ty)-affine.f)/affine.e-.5
        values=map_coordinates(array,[rows,cols],order=1,mode='constant',cval=np.nan,prefilter=False)
        if not np.all(np.isfinite(values)):
            no_data[0]+=int(np.sum(~np.isfinite(values)))
            raise RuntimeError(f'Missing DEM at {points[~np.isfinite(values)][:5].tolist()}')
        neg=values<0
        if np.any(neg):
            distances=shapely.distance(shapely.points(points[neg]),landcm.boundary)
            idx=np.flatnonzero(neg)[distances<10000*factor]
            if count:coastal_clamps[0]+=len(idx)
            values[idx]=0
        return values

    rx0,ry0,rx1,ry1=landcm.bounds
    bx0=rx0-c['TRAY_FRAME_WIDTH']; bx1=bx0+c['TRAY_WIDTH']
    by1=ry1+c['TRAY_FRAME_WIDTH']; by0=by1-c['TRAY_HEIGHT']
    if bx1<rx1+c['TRAY_FRAME_WIDTH'] or by0>ry0-c['TRAY_FRAME_WIDTH']:
        raise ValueError('Board does not contain the complete main map and frame')
    outer_board=box(bx0,by0,bx1,by1)
    inner_board=box(bx0+c['TRAY_FRAME_WIDTH'],by0+c['TRAY_FRAME_WIDTH'],
                    bx1-c['TRAY_FRAME_WIDTH'],by1-c['TRAY_FRAME_WIDTH']).buffer(c['NUMERICAL_GAP'],join_style=2)
    frame=outer_board.difference(inner_board)
    px1=rx1+c['INSET_RIGHT_OFFSET_FROM_MAP']
    placement=config['data']['south_sea_inset']['placement']
    if placement=='bottom_right':
        py0=by0+c['TRAY_FRAME_WIDTH']+c['INSET_MARGIN']
        py1=py0+c['INSET_PANEL_HEIGHT']
    elif placement=='top_right':
        py1=by1-c['TRAY_FRAME_WIDTH']-c['INSET_MARGIN']
        py0=py1-c['INSET_PANEL_HEIGHT']
    else:
        raise ValueError(f'Unsupported inset placement: {placement}')
    panel=box(px1-c['INSET_PANEL_WIDTH'],py0,px1,py1)
    inset_marks,inset_report=inset.build(config,PROJ/config['data']['boundary'],panel,projection,gcj_inverse)
    write_json(OUT/'south_sea_inset.geojson',{'type':'Feature','properties':{'role':'fixed_inset'},'geometry':mapping(inset_marks)})
    write_json(PROJ/'spec/inset_report.json',inset_report)
    high=c['TRAY_FLOOR']+c['SLOT_DEPTH']
    raised=[(frame,high+c['TRAY_FRAME_RISE']),(inset_marks,high+c['INSET_RAISE'])]
    usable=c['PRINT_BED']-2*c['PRINT_MARGIN']-c['TRAY_TAB_LENGTH']
    nx=math.ceil((bx1-bx0)/usable); ny=math.ceil((by1-by0)/usable)
    if [nx,ny]!=config['data']['required_tray_grid']:
        raise ValueError(f'Required tray grid does not fit the print bed: {nx} x {ny}')
    xs=np.linspace(bx0,bx1,nx+1); ys=np.linspace(by0,by1,ny+1)
    cells=[(ix,iy,box(xs[ix],ys[iy],xs[ix+1],ys[iy+1])) for iy in range(ny) for ix in range(nx)]
    nodes=[]; reports=[]; warnings=[]; pieces={}; assemblies={}; cards=[]; fixed=[]; features=[]
    min_h,max_h=math.inf,-math.inf
    fixed_codes=set(config['data']['fixed_province_codes'])
    for p in provinces:
        components=polygons(p['cm'])
        if p['code'] in fixed_codes:
            fixed.extend(components)
            features.append({'type':'Feature','properties':{'code':p['code'],'name':p['name'],'role':'fixed_to_base'},'geometry':mapping(p['cm'])})
            print(f'  {p["code"]} {p["name"]}: integrated into base',flush=True)
            continue
        primary=max(components,key=lambda g:g.area)
        tiny_holes=[r for r in primary.interiors if Polygon(r).area<c['MIN_HOLE_AREA']]
        if tiny_holes:
            primary=Polygon(primary.exterior,[r for r in primary.interiors if Polygon(r).area>=c['MIN_HOLE_AREA']])
            warnings.append({'code':p['code'],'kind':'sub_resolution_holes_filled','count':len(tiny_holes),'area_mm2':sum(Polygon(r).area for r in tiny_holes)*100})
        write_json(OUT/f'outline_{p["code"]}.geojson',{'type':'Feature','properties':{'code':p['code']},'geometry':mapping(primary)})
        fixed.extend(g for g in components if g is not max(components,key=lambda g:g.area))
        cards.append(primary)
        gb=primary.bounds; needs_split=max(gb[2]-gb[0],gb[3]-gb[1])>usable
        plans=cells if needs_split else [(None,None,None)]
        key=f'stl/province_assemblies/{p["code"]}_{p["name"]}'; assemblies[key]=[]
        for ix,iy,cell in plans:
            chunks=polygons(primary.intersection(cell)) if cell is not None else [primary]
            if not chunks:continue
            meshes=[]; hmin,hmax=math.inf,-math.inf
            for chunk in chunks:
                mesh,hrange=build_solid(chunk,lambda xy:sample(xy,count=True),c['TRAY_FLOOR'],c)
                meshes.append(mesh); hmin=min(hmin,hrange[0]); hmax=max(hmax,hrange[1])
            combined=trimesh.util.concatenate(meshes)
            suffix=f'_X{ix+1}_Y{iy+1}' if cell is not None else ''
            name=f'P{p["code"]}{suffix}'
            r=store_mesh(name,combined,{'group':'terrain','province':p['name'],'code':p['code'],'tile':[ix+1,iy+1] if cell is not None else [],'mount':'loose_card'},np.mean(combined.bounds,axis=0).tolist(),nodes)
            r.update(name=p['name'],code=p['code'],elevation_m=[hmin,hmax],pin_count=0)
            reports.append(r); pieces[f'stl/terrain/{p["code"]}_{p["name"]}{suffix}']=[name]; assemblies[key].append(name)
            min_h=min(min_h,hmin); max_h=max(max_h,hmax)
        features.append({'type':'Feature','properties':{'code':p['code'],'name':p['name'],'role':'removable_card'},'geometry':mapping(primary)})
        print(f'  {p["code"]} {p["name"]}: removable flat-bottom card',flush=True)
    card_union=unary_union(cards)
    if panel.intersection(card_union).area>1e-8:
        raise ValueError('Inset panel obstructs a removable province')
    fixed_union=unary_union(fixed).difference(card_union)
    # Resolve point contacts among fixed details at numeric scale; do not add
    # manufacturing gaps along borders between removable province cards.
    fs=polygons(fixed_union); close=set()
    for i,a in enumerate(fs):
        for j in range(i+1,len(fs)):
            if a.distance(fs[j])<c['NUMERICAL_GAP']:close.update([i,j])
    for index in sorted(close):
        contracted=fs[index].buffer(-c['NUMERICAL_GAP']/2,join_style=2)
        if not contracted.is_empty:fs[index]=contracted
    fixed_union=unary_union(fs)
    # Planar difference is the same footprint subtraction as using every
    # province as an equal-depth cutter, with a flat floor instead of DEM tops.
    # Fixed details also replace the slab surface locally and remain attached.
    recess=unary_union([card_union,fixed_union])
    recess_holes=[]
    recess_parts=[]
    for p in polygons(recess):
        recess_holes.extend(r for r in p.interiors if Polygon(r).area<c['MIN_HOLE_AREA'])
        recess_parts.append(Polygon(p.exterior,[r for r in p.interiors if Polygon(r).area>=c['MIN_HOLE_AREA']]))
    recess=unary_union(recess_parts)
    # A microscopic land/sea sliver can touch the surrounding slab only at
    # points, making its extruded vertical edges nonmanifold. Cut these residual
    # sub-resolution islands too; preserve all printable coastline detail.
    residual=[p for p in polygons(box(bx0,by0,bx1,by1).difference(recess))
              if p.area<c['MIN_HOLE_AREA']]
    if residual:
        recess=unary_union([recess,*residual])
        warnings.append({'kind':'recess_sub_resolution_residuals_removed','count':len(residual),
                         'area_mm2':sum(p.area for p in residual)*100})
    if recess_holes:
        warnings.append({'kind':'recess_sub_resolution_holes_filled','count':len(recess_holes),
                         'area_mm2':sum(Polygon(r).area for r in recess_holes)*100})
    write_json(OUT/'national_recess_nominal.geojson',{'type':'Feature','properties':{'depth_mm':c['SLOT_DEPTH']*10},'geometry':mapping(recess)})
    recess=recess.buffer(c['SLOT_CLEARANCE'],quad_segs=24,join_style='round')
    frame=frame.difference(recess)
    raised=[(frame,high+c['TRAY_FRAME_RISE']),(inset_marks,high+c['INSET_RAISE'])]
    write_json(OUT/'national_recess.geojson',{'type':'Feature','properties':{'depth_mm':c['SLOT_DEPTH']*10,'outward_offset_mm':c['SLOT_CLEARANCE']*10},'geometry':mapping(recess)})
    if close:warnings.append({'kind':'fixed_detail_numeric_contact_repair','component_count':len(close),'gap_mm':c['NUMERICAL_GAP']*10})
    for g in polygons(fixed_union):
        a,b,x,y=g.bounds
        if min(x-a,y-b)<c['MIN_FEATURE'] or g.area<c['MIN_FEATURE']**2:
            warnings.append({'kind':'fixed_detail_below_FDM_feature_size','area_mm2':g.area*100,'bbox_mm':[(x-a)*10,(y-b)*10]})
    print(f'Base: {nx} x {ny} tiles, integrated small regions and coastal details',flush=True)
    write_json(OUT/'fixed_details.geojson',{'type':'FeatureCollection','features':[{'type':'Feature','properties':{'role':'fixed_to_base'},'geometry':mapping(fixed_union)}]})
    for ix,iy,cell in cells:
        poly=tray_polygon(cell,ix,iy,nx,ny,c)
        if c.get('FIXED_DETAILS_FLUSH'):
            mesh=make_tray(poly,recess,c,raised_regions=[(fixed_union,high),(frame,high+c['TRAY_FRAME_RISE'])])
        else:
            mesh=make_tray(poly,recess,c,fixed_union,lambda xy:sample(xy,count=True),raised)
        name=f'Tray_X{ix+1}_Y{iy+1}'
        reports.append(store_mesh(name,mesh,{'group':'tray','tile':[ix+1,iy+1],'slot_depth_cm':c['SLOT_DEPTH'],'floor_cm':c['TRAY_FLOOR']},np.mean(mesh.bounds,axis=0).tolist(),nodes))
        pieces[f'stl/tray/{name}']=[name]
    for r in reports:
        if max(r['dimensions_mm'][:2])>c['PRINT_BED']*10:raise RuntimeError(f'Part exceeds bed: {r}')
    assert len([f for f in features if f['properties']['role']=='removable_card'])==32
    nodes.append({'name':'Export','op':'ops/export_model.py','after':[n['name'] for n in nodes],'params':{'pieces':dict(pieces,**assemblies),'blend_name':'china_relief.blend'}})
    config['nodes']=nodes
    fingerprint=hashlib.sha256(json.dumps({'constants':c,'data':config['data']},sort_keys=True).encode()).hexdigest()
    config['prepared_fingerprint']=fingerprint
    write_json(MODEL,config)
    # Check occupancy directly, independent of meshing: fixed details cannot block cards.
    blocked=fixed_union.intersection(card_union).area*100
    if blocked>1e-6:raise RuntimeError(f'Fixed details obstruct cards: {blocked} mm²')
    final_overlaps=[]
    for i,a in enumerate(cards):
        for j,b in enumerate(cards[i+1:],i+1):
            area=a.intersection(b).area*100
            if area>1e-6:final_overlaps.append({'a':i,'b':j,'area_mm2':area})
    assert not final_overlaps,final_overlaps
    report={'date':'2026-11-15','design_revision':config['design_revision'],
            'map_dimensions_mm':[c['MAP_WIDTH']*10,height*10],'tray_dimensions_mm':[(bx1-bx0)*10,(by1-by0)*10],
            'tray_bounds_cm':[bx0,by0,bx1,by1],'tray_grid':[nx,ny],
            'horizontal_scale_denominator':100/factor,'vertical_exaggeration':c['VERTICAL_EXAGGERATION'],
            'elevation_datum_m':c['ELEVATION_DATUM'],'sampled_elevation_range_m':[min_h,max_h],
            'max_assembly_height_mm':max(r['bounds_mm'][1][2] for r in reports),
            'province_count':34,'removable_province_count':32,'fixed_province_codes':sorted(fixed_codes),
            'terrain_part_count':sum(r['group']=='terrain' for r in reports),'tray_part_count':len(cells),'fit_coupon_count':0,
            'shared_recess_depth_mm':c['SLOT_DEPTH']*10,'recess_floor_thickness_mm':c['TRAY_FLOOR']*10,
            'recess_shape':'union_of_province_footprints_with_uniform_outward_offset','slot_outward_offset_mm':c['SLOT_CLEARANCE']*10,'recess_area_mm2':recess.area*100,
            'card_outside_recess_mm2':card_union.difference(recess).area*100,
            'frame_height_mm':(high+c['TRAY_FRAME_RISE'])*10,'frame_rise_above_platform_mm':c['TRAY_FRAME_RISE']*10,
            'inset':inset_report,'province_gap_mm':0,'province_partition_walls':False,
            'fixed_detail_component_count':len(polygons(fixed_union)),'fixed_card_overlap_mm2':blocked,
            'original_boundary_component_count':original_count,'omitted_nansha_component_count':len(omitted),
            'boundary_source':'DataV 2021 GeoJSON','boundary_crs_assumption':config['data']['boundary_coordinate_assumption'],
            'boundary_sha256':sha(PROJ/config['data']['boundary']),'boundary_repairs':repairs,
            'source_overlaps':overlaps,'topology_normalizations':normalizations,'card_overlaps':final_overlaps,
            'terrain_tile_count':len(entries),'terrain_mosaic_sha256':sha(OUT/'terrain_mosaic.tif'),
            'terrain_sources':sorted(set(e['source'] or 'unspecified' for _,e in entries)),
            'coastal_negative_sample_clamps':coastal_clamps[0],'missing_dem_samples':no_data[0],
            'warnings':warnings,'parts':reports,'prepared_fingerprint':fingerprint,
            'limitations':['Boundary CRS is assumed, not declared by provider.',
                           'No nominal clearance between province cards, as requested; real FDM parts may need edge trimming.',
                           'Fixed sub-nozzle details may be simplified by the slicer.',
                           'DataV redistribution license is unverified.',
                           'DEM/mesh resampling reduce summit heights; no manual summit adjustment.']}
    write_json(PROJ/'spec/data_report.json',report)
    write_json(OUT/'province_print_outlines.geojson',{'type':'FeatureCollection','features':features})
    write_json(OUT/'fixed_details.geojson',{'type':'FeatureCollection','features':[{'type':'Feature','properties':{'role':'fixed_to_base'},'geometry':mapping(fixed_union)}]})
    print(f'Prepared {len(nodes)-1} meshes; 32 movable cards, {len(cells)} bases; {len(omitted)} Nansha components restored in fixed inset',flush=True)


if __name__=='__main__':
    main()
