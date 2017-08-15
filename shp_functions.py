import shapely.geometry as sgeom
import numpy as np

#this function was taken from cartopy
def create_polygon(shape):
    if not shape.points:
        return sgeom.MultiPolygon()

    # Partition the shapefile rings into outer rings/polygons (clockwise) and
    # inner rings/holes (anti-clockwise).
    parts = list(shape.parts) + [None]
    bounds = zip(parts[:-1], parts[1:])
    outer_polygons_and_holes = []
    inner_polygons = []
    for lower, upper in bounds:
        polygon = sgeom.Polygon(shape.points[slice(lower, upper)])
        if polygon.exterior.is_ccw:
            inner_polygons.append(polygon)
        else:
            outer_polygons_and_holes.append((polygon, []))

    # Find the appropriate outer ring for each inner ring.
    # aka. Group the holes with their containing polygons.
    for inner_polygon in inner_polygons:
        for outer_polygon, holes in outer_polygons_and_holes:
            if outer_polygon.contains(inner_polygon):
                holes.append(inner_polygon.exterior.coords)
                break

    polygon_defns = [(outer_polygon.exterior.coords, holes)
                     for outer_polygon, holes in outer_polygons_and_holes]
    return sgeom.MultiPolygon(polygon_defns)

def inpolygon(polygon, xp, yp):
	return np.array([sgeom.Point(x,y).intersects(polygon) for x,y in zip(xp,yp)],dtype=np.bool)

def create_mask(coords, grid_resolution, polygon):
    lato = np.array(coords['lat'])
    lono = np.array(coords['lon'])
    lati = np.linspace(min(lato), max(lato), grid_resolution)
    loni = np.linspace(min(lono), max(lono), grid_resolution)
    glon, glat = np.meshgrid(loni, lati)
    mask = inpolygon(polygon, glon.ravel(), glat.ravel()).reshape(glon.shape)
    mask_list = mask.tolist()

    return mask
