# -*- coding: utf-8 -*-
""" Main window.

Copyright (c) Karol Będkowski, 2015

This file is part of tbviewer
Licence: GPLv2+
"""

__author__ = "Karol Będkowski"
__copyright__ = "Copyright (c) Karol Będkowski, 2015"
__version__ = "2015-05-10"

import os.path
import collections


class InvalidFileException(RuntimeError):
    pass


def parse_map(content):
    content = [line.decode('ascii').strip() for line in content]
    # OziExplorer Map Data File Version 2.2
    if str(content[0]) != 'OziExplorer Map Data File Version 2.2':
        print(repr(content[0]))
        print(type(content[0]))
        raise InvalidFileException("Wrong header %r" % content[0])
    # janow.jpg
    # -- filename
    filename = os.path.splitext(content[1])[0]
    # C:\Program Files\PFE\MapoTero\download\janow.jpg
    # -- file with path
    # 1 ,Map Code,
    # WGS 84,,0.0000,0.0000,
    # Reserved 1
    # Reserved 2
    # Magnetic Variation,,,E                                                                                                                                                  Map Projection,Transverse Mercator,PolyCal,No,AutoCalOnly,No,BSBUseWPX,No
    # Point01,xy,    0,    0,
    # Point02,xy, 6656,    0,
    # Point03,xy, 6656, 7680,
    # Point04,xy,    0, 7680,
    # Point05,xy,     ,     ,
    # Point06,xy,     ,     ,
    # Point07,xy,     ,     ,
    # Point08,xy,     ,     ,
    # Point09,xy,     ,     ,
    # Point10,xy,     ,     ,
    # Point11,xy,     ,     ,
    # Point12,xy,     ,     ,
    # Point13,xy,     ,     ,
    # Point14,xy,     ,     ,
    # Point16,xy,     ,     ,
    # Point17,xy,     ,     ,
    # Point18,xy,     ,     ,
    # Point19,xy,     ,     ,
    # Point20,xy,     ,     ,
    # Point21,xy,     ,     ,
    # Point22,xy,     ,     ,
    # Point23,xy,     ,     ,
    # Point24,xy,     ,     ,
    # Point25,xy,     ,     ,
    # Point26,xy,     ,     ,
    # Point27,xy,     ,     ,
    # Point28,xy,     ,     ,
    # Point29,xy,     ,     ,
    # Point30,xy,     ,     ,
    # Projection Setup,     0
    # Map Feature = MF ; Map Comment = MC     These follow if they exist
    # Track File = TF      These follow if they exist
    # Moving Map Parameters = MM?    These follow if they exist
    # MM0,Yes
    # MMPNUM,4
    # MMPXY,1,0,0
    # MMPXY,2,6656,0
    # MMPXY,3,6656,7680
    # MMPXY,4,0,7680
    # MMPLL,1,  19.23346,  50.85753
    # MMPLL,2,  19.611825,  50.85616                                                                                                                                          MMPLL,3,  19.608237,  50.57983
    # MMPLL,4,   19.232091,  50.581187
    # MM1B,     4
    # MOP,Map Open Position,0,0
    # IWH,Map Image Width/Height,6656,7680
    lwidthheight = content[55]
    if not lwidthheight.startswith('IWH,Map Image Width/Height,'):
        raise InvalidFileException("missing widh/height")
    width, height = map(int, lwidthheight[27:].split(','))
    return {'filename': filename, 'width': width, 'height': height}


def parse_set_file(content):
    rows = collections.defaultdict(dict)
    for line in sorted(l.decode().strip() for l in content):
        # basename_y_x.png
        name = os.path.splitext(line)[0]
        dummy, y, x = name.split('_')
        y = int(y)
        x = int(x)
        rows[y][x] = line
    return rows


def load_tar(tarfile):
    files = tarfile.getnames()
    # find map in root
    mapfile = [fname for fname in files
               if '/' not in fname and fname.endswith('.map')]
    if not mapfile:
        raise InvalidFileException('map file not found')
    mapfile = mapfile[0]
    # find set file
    setfile = [fname for fname in files
               if '/' not in fname and fname.endswith('.set')]
    if not setfile:
        raise InvalidFileException('set file not found')
    setfile = setfile[0]

    # load map
    map_data = None
    with tarfile.extractfile(mapfile) as mfile:
        content = mfile.readlines()
        map_data = parse_map(content)

    # load set file
    set_data = None
    with tarfile.extractfile(setfile) as sfile:
        content = sfile.readlines()
        set_data = parse_set_file(content)

    return map_data, set_data
