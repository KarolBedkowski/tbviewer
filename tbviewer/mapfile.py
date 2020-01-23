#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright (c) Karol Będkowski, 2020
# This file is part of tbviewer
#
# Distributed under terms of the GPLv3 license.

"""

"""
import logging
import math

from . import formatting

_LOG = logging.getLogger(__name__)


class InvalidFileException(RuntimeError):
    pass


class Point:
    def __init__(self, x, y, lon, lat, idx=None):
        self.idx = idx
        self.x = x
        self.y = y
        self.lat = lat
        self.lon = lon

    def __repr__(self):
        return formatting.prettydict(self.__dict__)


def degree2minsec(d, lz='S', gz='N'):
    symb = gz
    if d < 0:
        d *= -1
        symb = lz

    return int(d), (d - int(d)) * 60, symb


class MapFile():
    def __init__(self):
        self.clear()

    def clear(self):
        self.filename = None
        self.img_filename = None
        self.img_filepath = None
        self.projection = None
        self.map_projection = None
        self.points = []
        # x, y
        self.mmpxy = []
        # lon, lat
        self.mmpll = []
        self.mmpnum = None
        self.mm1b = None
        self.image_width = None
        self.image_height = None

    def __str__(self):
        return "<MapMeta {}>".format(", ".join(
            "{}={}".format(k, v)
            for k, v in self.__dict__.items()
            if k[0] != '_'
        ))

    def parse_map(self, content):
        """Parse content of .map file."""
        self.clear()
        content = [line.strip() for line in content.split("\n")]
        if content[0] != 'OziExplorer Map Data File Version 2.2':
            raise InvalidFileException(
                "Wrong .map file - wrong header %r" % content[0])

        if len(content) < 10:
            raise InvalidFileException("Wrong .map file - too short")

        self.img_filename = content[1]
        self.img_filepath = content[2]
        # line 3 - skip
        self.projection = content[4]
        # line 5-6 - reserverd
        # line 7 - Magnetic variation
        self.map_projection = content[8]

        for line in content[9:]:
            try:
                if line.startswith("Point"):
                    point = _parse_point(line)
                    if point:
                        self.points.append(point)
                elif line.startswith('IWH,Map Image Width/Height,'):
                    self.image_width, self.image_height = \
                        map(int, line[27:].split(','))
                elif line.startswith('MMPNUM,'):
                    self.mmpnum = int(line[7:])
                elif line.startswith('MMPLL'):
                    point_id, lon, lat = _parse_mmpll(line)
                    if point_id - 1 != len(self.mmpll):
                        raise InvalidFileException("Invalid MMPLL point id")
                    self.mmpll.append((lon, lat))
                elif line.startswith('MMPXY'):
                    point_id, x, y = _parse_mmpxy(line)
                    if point_id - 1 != len(self.mmpxy):
                        _LOG.warn("parse mmpxy error: %r", line)
                        raise InvalidFileException("Invalid MMPXY point index")
                    self.mmpxy.append((x, y))
                elif line.startswith('MM1B,'):
                    self.mm1b = float(line[5:])
            except ValueError as err:
                raise InvalidFileException(
                    f"Error loading line '{line}': {err}")

    def to_str(self):
        points = []
        for idx, p in enumerate(self.points):
            _LOG.debug("Point %r", p)
            lat_m, lat_s, lat_d = degree2minsec(p.lat, 'S', 'N')
            lon_m, lon_s, lon_d = degree2minsec(p.lon, 'W', 'E')
            points.append(_MAP_POINT_TEMPLATE.format(
                idx=idx, x=int(p.x), y=int(p.y),
                lat_m=lat_m, lat_s=lat_s, lat_d=lat_d,
                lon_m=lon_m, lon_s=lon_s, lon_d=lon_d
            ))
        mmpxy = [_MAP_MMPXY_TEMPLATE.format(idx=idx+1, x=x, y=y)
                 for idx, (x, y) in enumerate(self.mmpxy)]
        mmpll = [_MAP_MMPLL_TEMPLATE.format(idx=idx+1, lat=lat, lon=lon)
                 for idx, (lon, lat) in enumerate(self.mmpll)]
        return _MAP_TEMPALTE.format(
            img_filename=self.img_filename or "dummy.jpg",
            img_filepath=self.img_filepath or "dummy.jpg",
            points="\n".join(points),
            mmplen=len(mmpxy),
            mmpxy="\n".join(mmpxy),
            mmpll="\n".join(mmpll),
            mm1b=self.mm1b,
            image_width=self.image_width,
            image_height=self.image_height
        )

    def set_points(self, points):
        _LOG.debug("points: %r", points)
        self.points = points

    def calibrate(self):
        points = _calibrate_calculate(self.points, self.image_width,
                                      self.image_height)
        self.mmpll = []
        self.mmpxy = []
        for p in points:
            self.mmpxy.append((p.x, p.y))
            self.mmpll.append((p.lon, p.lat))

        _LOG.debug("mmpll: %r", self.mmpll)

        self.mmpnum = len(self.mmpll)

        # calc MM1B - The scale of the image meters/pixel, its
        # calculated in the left / right image direction.
        lon_w_avg = (self.mmpll[0][0] + self.mmpll[3][0]) / 2
        lon_e_avg = (self.mmpll[1][0] + self.mmpll[2][0]) / 2
        lat_avg = (self.mmpll[0][1] + self.mmpll[3][1] +
                   self.mmpll[1][1] + self.mmpll[2][1]) / 4
        d_lon = lon_e_avg - lon_w_avg
        d_lon_dist = abs(d_lon * math.pi / 180.0 * 6378137.0 *
                         math.cos(math.radians(lat_avg)))

        self.mm1b = d_lon_dist / self.image_width

    def validate(self):
        _LOG.debug("mapfile: %s", self)
        return self.mmpnum == len(self.mmpxy) == len(self.mmpll) == 4

    def xy2latlon(self, x, y):
        if not self.mmpll:
            return None
        return _map_xy_lonlat(
            self.mmpll[0], self.mmpll[1], self.mmpll[2], self.mmpll[3],
            self.image_width, self.image_height,
            x, y)


def _parse_point(line):
    _LOG.debug("_parse_point %r", line)
    fields = line.split(',')
    if fields[2].strip() == "":
        return None
    point = Point(
        x=int(fields[2]),
        y=int(fields[3]),
        lat=int(fields[6]) + float(fields[7]) / 60.,
        lon=int(fields[9]) + float(fields[10]) / 60.)
    point.idx = int(fields[0][5:])
    if fields[8] == 'E':
        point.lon *= -1
    if fields[11] == 'S':
        point.lat *= -1
    return point


def _parse_mmpxy(line):
    fields = line.split(',')
    if len(fields) != 4:
        raise InvalidFileException(
            "Wrong .map file - wrong number of fields in MMPXY field %r"
            % line)
    _, point_id, x, y = [field.strip() for field in fields]
    try:
        point_id = int(point_id)
        x = int(x)
        y = int(y)
    except ValueError as err:
        raise InvalidFileException(
            "Wrong .map file - wrong MMPXY field %r; %s" % (line, err))
    return point_id, x, y


def _parse_mmpll(line):
    fields = line.split(',')
    if len(fields) != 4:
        raise InvalidFileException(
            "Wrong .map file - wrong number of fields in MMPLL field %r"
            % line)
    _, point_id, lon, lat = [field.strip() for field in fields]
    try:
        point_id = int(point_id)
        lon = float(lon)
        lat = float(lat)
    except ValueError as err:
        raise InvalidFileException(
            "Wrong .map file - wrong MMPLL field %r; %s" % (line, err))
    return point_id, lon, lat


def _sort_points(positions, width, height):
    if not positions or len(positions) < 2:
        return []

    def dist_from(pos, x0, y0):
        return math.sqrt((pos.x - x0) ** 2 + (pos.y - y0) ** 2)

    # north, w-e
    t_pos = sorted(positions, key=lambda x: dist_from(x, 0, 0))
    n_nw = t_pos[0]
    n_ne = sorted(t_pos[1:], key=lambda x: dist_from(x, width, 0))[0]
    top = (n_nw, n_ne)

    # south, w-e
    t_pos = sorted(positions, key=lambda x: dist_from(x, 0, height))
    s_sw = t_pos[0]
    s_se = sorted(t_pos[1:], key=lambda x: dist_from(x, width, height))[0]
    bottom = (s_sw, s_se)

    # west, n-s
    t_pos = sorted(positions, key=lambda x: dist_from(x, 0, 0))
    w_nw = t_pos[0]
    w_sw = sorted(t_pos[1:], key=lambda x: dist_from(x, 0, height))[0]
    left = (w_nw, w_sw)

    # east, n-s
    t_pos = sorted(positions, key=lambda x: dist_from(x, width, 0))
    e_ne = t_pos[0]
    e_se = sorted(t_pos[1:], key=lambda x: dist_from(x, width, height))[0]
    right = (e_ne, e_se)

    return (left, right, top, bottom)


def _calibrate_calculate(positions, width, height):
    _LOG.debug("calibrate_calculate: %r, %r, %r", positions, width, height)
    left, right, top, bottom = _sort_points(positions, width, height)

    # west/east - north
    nw, ne = top
    ds = (nw.lon - ne.lon) / (nw.x - ne.x)
    nw_lon = nw.lon - ds * nw.x
    ne_lon = nw_lon + ds * width
    _LOG.debug("top: %r ds=%r nw_lon=%r, ne_lon=%r", top, ds, nw_lon, ne_lon)

    # west/east - south
    sw, se = bottom
    ds = (se.lon - sw.lon) / (se.x - sw.x)
    sw_lon = sw.lon - ds * sw.x
    se_lon = sw_lon + ds * width
    _LOG.debug("bottom: %r ds=%r", bottom, ds)

    # north / south - west
    nw, sw = left
    ds = (nw.lat - sw.lat) / (nw.y - sw.y)
    nw_lat = nw.lat - ds * nw.y
    sw_lat = nw_lat + ds * height
    _LOG.debug("left: %r ds=%r", left, ds)

    # north / south - east
    ne, se = right
    ds = (ne.lat - se.lat) / (ne.y - se.y)
    ne_lat = ne.lat - ds * ne.y
    se_lat = ne_lat + ds * height
    _LOG.debug("right: %r ds=%r", right, ds)

    res = [
        Point(0,     0,      nw_lon, nw_lat, 0),  # nw
        Point(width, 0,      ne_lon, ne_lat, 1),  # ne
        Point(width, height, se_lon, se_lat, 2),  # se
        Point(0,     height, sw_lon, sw_lat, 3)  # sw
    ]
    _LOG.debug("_calibrate_calculate %r", res)
    return res


def _map_xy_lonlat(xy0, xy1, xy2, xy3, sx, sy, x, y):
    x0, y0 = xy0
    x1, y1 = xy1
    x2, y2 = xy2
    x3, y3 = xy3

    syy = sy - y
    sxx = sx - x

    return _intersect_lines(
        (syy * x0 + y * x3) / sy, (syy * y0 + y * y3) / sy,
        (syy * x1 + y * x2) / sy, (syy * y1 + y * y2) / sy,
        (sxx * x0 + x * x1) / sx, (sxx * y0 + x * y1) / sx,
        (sxx * x3 + x * x2) / sx, (sxx * y3 + x * y2) / sx)


def _det(a, b, c, d):
    return a * d - b * c


def _intersect_lines(x1, y1, x2, y2, x3, y3, x4, y4):
    d = _det(x1 - x2, y1 - y2, x3 - x4, y3 - y4) or 1
    d1 = _det(x1, y1, x2, y2)
    d2 = _det(x3, y3, x4, y4)
    px = _det(d1, x1 - x2, d2, x3 - x4) / d
    py = _det(d1, y1 - y2, d2, y3 - y4) / d
    return px, py


def distance(lat1, lon1, lat2, lon2):
    dlat2 = math.radians(lat2 - lat1) / 2.
    dlon2 = math.radians(lon2 - lon1) / 2.
    lat1 = math.radians(lat1)
    lat2 = math.radians(lat2)
    a = math.sin(dlat2) * math.sin(dlat2) + \
        math.cos(lat1) * math.cos(lat2) * math.sin(dlon2) * math.sin(dlon2)
    return 12742. * math.atan2(math.sqrt(a), math.sqrt(1 - a))


_MAP_POINT_TEMPLATE = \
    "Point{idx:02d},xy,{x:>5},{y:>5},in, deg,{lat_m:>4},{lat_s:3.7f},{lat_d},"\
    "{lon_m:>4},{lon_s:3.7f},{lon_d}, grid,   ,           ,           ,N"

_MAP_MMPXY_TEMPLATE = "MMPXY,{idx},{x},{y}"
_MAP_MMPLL_TEMPLATE = "MMPLL,{idx},{lon:3.7f},{lat:3.7f}"

_MAP_TEMPALTE = """OziExplorer Map Data File Version 2.2
{img_filename}
{img_filepath}
1 ,Map Code,
WGS 84,WGS 84,   0.0000,   0.0000,WGS 84
Reserved 1
Reserved 2
Magnetic Variation,,,E
Map Projection,Latitude/Longitude,PolyCal,No,AutoCalOnly,No,BSBUseWPX,No
{points}
Projection Setup,,,,,,,,,,
Map Feature = MF ; Map Comment = MC     These follow if they exist
Track File = TF      These follow if they exist
Moving Map Parameters = MM?    These follow if they exist
MM0,Yes
MMPNUM,{mmplen}
{mmpxy}
{mmpll}
MM1B,{mm1b}
MOP,Map Open Position,0,0
IWH,Map Image Width/Height,{image_width},{image_height}
"""
