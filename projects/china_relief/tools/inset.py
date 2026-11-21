"""Fixed cartographic inset, preserving every source component in its extent."""
import json
import numpy as np
import shapely
from shapely.geometry import Polygon, box, shape
from shapely.ops import unary_union, transform
from shapely.affinity import scale, translate
from fontTools.ttLib import TTFont
from fontTools.pens.basePen import BasePen


def parts(g):
    if isinstance(g, Polygon): return [g] if not g.is_empty else []
    return [p for child in getattr(g,'geoms',[]) for p in parts(child)]


class OutlinePen(BasePen):
    def __init__(self, glyphs):
        super().__init__(glyphs); self.contours=[]; self.points=[]
    def _moveTo(self,p): self.points=[p]
    def _lineTo(self,p): self.points.append(p)
    def _curveToOne(self,a,b,c):
        start=np.array(self.points[-1]); a,b,c=map(np.array,(a,b,c))
        for t in np.linspace(0,1,13)[1:]:
            self.points.append(tuple((1-t)**3*start+3*(1-t)**2*t*a+3*(1-t)*t*t*b+t**3*c))
    def _qCurveToOne(self,a,b):
        start=np.array(self.points[-1]); a,b=map(np.array,(a,b))
        for t in np.linspace(0,1,13)[1:]:
            self.points.append(tuple((1-t)**2*start+2*(1-t)*t*a+t*t*b))
    def _closePath(self):
        if len(self.points)>2: self.contours.append(self.points)
        self.points=[]
    def _endPath(self): self._closePath()


def text_shape(font, text, size, origin):
    glyphs=font.getGlyphSet(); cmap=font.getBestCmap(); units=font['head'].unitsPerEm
    shapes=[]; cursor=0
    for char in text:
        if ord(char) not in cmap: raise ValueError(f'Missing font glyph: {char}')
        name=cmap[ord(char)]; pen=OutlinePen(glyphs); glyphs[name].draw(pen)
        g=Polygon()
        for ring in pen.contours:
            g=g.symmetric_difference(shapely.make_valid(Polygon(ring)))
        shapes.append(translate(g,xoff=cursor)); cursor+=font['hmtx'][name][0]
    g=scale(unary_union(shapes),xfact=size/units,yfact=size/units,origin=(0,0))
    return translate(g,xoff=origin[0],yoff=origin[1])


def build(config, raw_path, panel, projection, gcj_inverse):
    c=config['constants']; settings=config['data']['south_sea_inset']
    clip=box(*settings['bounds_lonlat']); raw=json.loads(raw_path.read_text())
    context=[]; islands=[]; dashes=[]; records=[]
    for feature in raw['features']:
        original=parts(shapely.make_valid(shape(feature['geometry'])))
        primary=max(original,key=lambda g:g.area) if original else None
        code=feature['properties'].get('adcode')
        for index,g in enumerate(original):
            clipped=g.intersection(clip)
            if clipped.is_empty: continue
            dest=dashes if code=='100000_JD' else context if g is primary else islands
            projected=transform(projection.transform,transform(gcj_inverse,clipped))
            dest.append(projected)
            records.append({'code':code,'source_component':index,'kind':'dash' if dest is dashes else 'context' if dest is context else 'island',
                            'source_bounds_lonlat':list(g.bounds)})
    all_shapes=context+islands+dashes
    minx,miny,maxx,maxy=unary_union(all_shapes).bounds
    x0,y0,x1,y1=panel.bounds; pad=c['INSET_PADDING']
    factor=min((x1-x0-2*pad)/(maxx-minx),
               (y1-y0-c['INSET_MAP_TOP_PAD']-c['INSET_MAP_BOTTOM_PAD'])/(maxy-miny))
    cx=(x0+x1)/2; cy=(y0+c['INSET_MAP_BOTTOM_PAD']+y1-c['INSET_MAP_TOP_PAD'])/2
    def place(g):
        return translate(scale(g,xfact=factor,yfact=factor,origin=((minx+maxx)/2,(miny+maxy)/2)),
                         xoff=cx-(minx+maxx)/2,yoff=cy-(miny+maxy)/2)
    def label_pos(lonlat):
        lon,lat=gcj_inverse(*lonlat); x,y=projection.transform(lon,lat)
        return (cx+(x-(minx+maxx)/2)*factor,cy+(y-(miny+maxy)/2)*factor)
    symbols=[]; enlarged=0
    symbols.append(place(unary_union(context)).boundary.buffer(c['INSET_LINE_WIDTH']/2))
    for g in islands:
        g=place(g); a,b,x,y=g.bounds
        if min(x-a,y-b)<c['INSET_MIN_ISLAND_WIDTH']:
            g=g.buffer(c['INSET_MIN_ISLAND_WIDTH']/2); enlarged+=1
        symbols.append(g)
    for g in dashes:
        symbols.append(place(g).buffer(c['INSET_LINE_WIDTH']/2))
    border=panel.difference(panel.buffer(-c['INSET_LINE_WIDTH'],join_style=2))
    font=TTFont(settings['font'],fontNumber=0)
    symbols.append(border)
    symbols.append(text_shape(font,settings['title'],c['INSET_TITLE_SIZE'],(x0+pad,y1-c['INSET_MAP_TOP_PAD']/2)))
    symbols.append(text_shape(font,settings['scale_note'],c['INSET_LABEL_SIZE'],(x0+pad,y0+pad)))
    for label in settings['labels']:
        symbols.append(text_shape(font,label['text'],c['INSET_LABEL_SIZE'],label_pos(label['lonlat'])))
    font.close()
    raised=unary_union(symbols)
    # Resolve point contacts in glyphs and schematic marks below print resolution.
    raised=raised.buffer(c['NUMERICAL_GAP'],join_style=2).buffer(-c['NUMERICAL_GAP'],join_style=2)
    raised=shapely.set_precision(raised,c['NUMERICAL_GAP']/10)
    raised=raised.simplify(c['NUMERICAL_GAP']/10,preserve_topology=True)
    # Keep the rounded coordinates but do not propagate a grid precision model
    # into tile intersections: their thirds need full precision at shared seams.
    raised=shapely.set_precision(raised,0)
    if not panel.buffer(c['NUMERICAL_GAP']).covers(raised):
        raise ValueError('Inset label or symbol extends outside panel')
    assert sum(r['code']=='100000_JD' for r in records)==len(dashes)==10
    assert sum(r['code']==460000 for r in records)==133
    return raised,{'source_component_count':len(records),'dash_count':len(dashes),
                   'hainan_source_component_count':133,'island_symbol_count':len(islands),
                   'enlarged_small_island_count':enlarged,'projection_cm_per_m':factor,
                   'panel_bounds_cm':list(panel.bounds),'labels':[settings['title'],settings['scale_note']]+[s['text'] for s in settings['labels']],
                   'records':records,'omitted_source_components':0,'dem_used':False}
