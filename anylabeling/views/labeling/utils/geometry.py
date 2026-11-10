"""Exact polygon boolean operations on annotation shapes, via shapely."""

import math

from shapely.geometry import Point, Polygon
from shapely.validation import make_valid

# Shape types that enclose an area and can therefore cut other shapes.
AREA_SHAPE_TYPES = (
    "polygon",
    "rectangle",
    "rotation",
    "quadrilateral",
    "circle",
)


def shape_geometry(shape_type, points, holes=()):
    """Build a valid shapely geometry for a closed annotation shape.

    Args:
        shape_type (str): One of ``AREA_SHAPE_TYPES``.
        points (list): Outer ring as ``(x, y)`` pairs; for a circle, its center and a point on the rim.
        holes (list): Inner rings of a polygon, each a list of ``(x, y)`` pairs.

    Returns:
        A shapely geometry, or ``None`` when the shape encloses no area.
    """
    if shape_type == "circle":
        if len(points) != 2:
            return None
        (cx, cy), (x, y) = points
        radius = math.hypot(x - cx, y - cy)
        return Point(cx, cy).buffer(radius) if radius > 0 else None
    if shape_type not in AREA_SHAPE_TYPES or len(points) < 3:
        return None
    geometry = Polygon(points, [ring for ring in holes if len(ring) >= 3])
    if not geometry.is_valid:
        # Self-intersecting hand-drawn outlines are common; repair rather than reject them.
        geometry = make_valid(geometry)
    return None if geometry.is_empty else geometry


def _polygons(geometry):
    """Yield the polygons inside any (nested) shapely geometry."""
    if geometry.geom_type == "Polygon":
        yield geometry
    elif hasattr(geometry, "geoms"):
        for part in geometry.geoms:
            yield from _polygons(part)


def subtract_geometry(target, cutter, min_area=1.0):
    """Cut ``cutter`` out of ``target`` and split the rest into pieces.

    Args:
        target: The shapely geometry being split.
        cutter: The shapely geometry removed from it.
        min_area (float): Pieces smaller than this, in square pixels, are dropped as slivers.

    Returns:
        list: ``(outer, holes)`` per piece, largest first, with rings as lists of ``(x, y)`` pairs and no repeated closing point.
    """
    pieces = [
        piece
        for piece in _polygons(target.difference(cutter))
        if piece.area >= min_area
    ]
    pieces.sort(key=lambda piece: piece.area, reverse=True)
    return [
        (
            list(piece.exterior.coords)[:-1],
            [list(ring.coords)[:-1] for ring in piece.interiors],
        )
        for piece in pieces
    ]
