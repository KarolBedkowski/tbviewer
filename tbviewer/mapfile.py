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


_LOG = logging.getLogger(__name__)


class InvalidFileException(RuntimeError):
    pass


class Point:
    def __init__(self, x, y, lat, lon):
        self.idx = None
        self.x = x
        self.y = y
        self.lat = lat
        self.lon = lon

    def __repr__(self):
        return prettydict(self.__dict__)


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
        self.filepath = None
        self.projection = None
        self.map_projection = None
        self.points = []
        self.mmpxy = []
        self.mmpll = []
        self.mmpnum = None
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

        self.filename = content[1]
        self.filepath = content[2]
        # line 3 - skip
        self.projection = content[4]
        # line 5-6 - reserverd
        # line 7 - Magnetic variation
        self.map_projection = content[8]

        for line in content[9:]:
            if line.startswith("Point"):
                point = _parse_point(line)
                if point:
                    self.points.append(point)
            elif line.startswith('IWH,Map Image Width/Height,'):
                self.image_width, self.image_height = \
                    map(int, line[27:].split(','))
            elif line.startswith('MMPLL'):
                point_id, lon, lat = _parse_mmpll(line)
                if point_id - 1 != len(self.mmpll):
                    raise Error()
                self.mmpll.append((lat, lon))
            elif line.startswith('MMPXY'):
                point_id, x, y = _parse_mmpxy(line)
                if point_id - 1 != len(self.mmpxy):
                    _LOG.warn("parse mmpxy error: %r", line)
                    raise InvalidFileException()
                self.mmpxy.append((x, y))

    def to_str(self):
        points = []
        for idx, p in enumerate(self.points):
            lat_m, lat_s, lat_d = degree2minsec(p.lat)
            lon_m, lon_s, lon_d = degree2minsec(p.lon)
            points.append(_MAP_POINT_TEMPLATE.format(
                idx=idx, x=int(p.x), y=int(p.y),
                lat_m=lat_m, lat_s=lat_s, lat_d=lat_d,
                lon_m=lon_m, lon_s=lon_s, lon_d=lon_d
            ))
        mmpxy = [_MAP_MMPXY_TEMPLATE.format(idx=idx+1, x=x, y=y)
                 for idx, (x, y) in enumerate(self.mmpxy)]
        mmpll = [_MAP_MMPLL_TEMPLATE.format(idx=idx+1, lat=lat, lon=lon)
                 for idx, (lat, lon) in enumerate(self.mmpll)]
        return _MAP_TEMPALTE.format(
            filename="dummy.jpg",
            filepath="dummy.jpg",
            points="\n".join(points),
            mmplen=0,
            mmpxy="\n".join(mmpxy),
            mmpll="\n".join(mmpll),
            image_width=self.image_width, image_height=self.image_height
        )

    def set_points(self, points):
        _LOG.debug("points: %r", points)
        self.points = [Point(x, y, lat, lon)
                       for x, y, lat, lon in points]

    def calibrate(self):
        mmp = calibrate_calculate(self.points, self.image_width,
                                  self.image_height)
        self.mmpll = []
        self.mmpxy = []
        for x, y, lat, lon in mmp:
            self.mmpxy.append((x, y))
            self.mmpll.append((lat, lon))

    def validate(self):
        return self.mmpnum == len(self.mmpxy) == len(self.mmpll)


def _parse_point(line):
    fields = line.split(',')
    if fields[2].strip() == "":
        return None
    point = Point(
        int(fields[2]), int(fields[3]),
        int(fields[6]) + float(fields[7]) / 60.,
        int(fields[9]) + float(fields[10]) / 60.)
    point.idx = int(fields[0][6:])
    if fields[8] == 'E':
        point.lat *= -1
    if fields[11] == 'S':
        point.lon *= -1
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


def sort_points(positions, width, height):
    def dist_from(pos, x0, y0):
        return math.sqrt((pos.x - x0) ** 2 + (pos.y - y0) ** 2)

    positions = sorted(positions, key=lambda x: dist_from(x, 0, 0))
    nw, positions = positions[0], positions[1:]
    positions = sorted(positions, key=lambda x: dist_from(x, width, 0))
    ne, positions = positions[0], positions[1:]
    positions = sorted(positions, key=lambda x: dist_from(x, 0, height))
    sw, se = positions
    _LOG.debug(repr(locals()))
    return (nw, ne, se, sw)


def calibrate_calculate(positions, width, height):
    _LOG.debug("calibrate_calculate: %r, %r, %r", positions, width, height)
    poss = sort_points(positions, width, height)
    p0, p1, p2, p3 = poss

    # west/east
    dlat = p0.lat - p2.lat
    dx = p0.x - p2.x
    w_lat = p0.lat - (dlat / dx) * p0.x
    e_lat = w_lat + (dlat / dx) * width

    # north / south
    dlon = p0.lon - p2.lon
    dy = p0.y - p2.y
    n_lon = p0.lon - (dlon / dy) * p0.y
    s_lon = n_lon + (dlon / dy) * height
    _LOG.debug(prettydict(locals()))

    return [
        (0, 0, w_lat, n_lon),
        (width, 0, e_lat, n_lon),
        (width, height, e_lat, s_lon),
        (0, height, w_lat, s_lon)
    ]


def prettydict(d):
    return "\n".join(
        str(key) + "=" + repr(val)
        for key, val in sorted(d.items())
    )


_MAP_POINT_TEMPLATE = \
    "Point{idx},xy,{x:>5},{y:>5},in, deg,{lat_m:>4},{lat_s:3.7f},{lat_d},"\
    "{lon_m:>4},{lon_s:3.7f},{lon_d}, grid,   ,           ,           ,N"

_MAP_MMPXY_TEMPLATE = "MMPXY,{idx},{x},{y}"
_MAP_MMPLL_TEMPLATE = "MMPLL,{idx},{lat:>11},{lon:>11}"

_MAP_TEMPALTE = """OziExplorer Map Data File Version 2.2
{filename}
{filepath}
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
MM1B,4.450529
MOP,Map Open Position,0,0
IWH,Map Image Width/Height,{image_width},{image_height}
"""
