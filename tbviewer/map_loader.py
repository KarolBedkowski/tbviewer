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
    content = [line.decode('cp1250').strip() for line in content]
    # OziExplorer Map Data File Version 2.2
    if str(content[0]) != 'OziExplorer Map Data File Version 2.2':
        raise InvalidFileException("Wrong header %r" % content[0])
    result = {'filename': os.path.splitext(content[1])[0]}
    for line in content[2:]:
        if line.startswith('IWH,Map Image Width/Height,'):
            result['width'], result['height'] = map(int, line[27:].split(','))
    if 'width' not in result:
        raise InvalidFileException("missing widh/height")
    return result


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


def is_atlas(tarfile):
    files = tarfile.getnames()
    mapfile = [fname for fname in files
               if '/' not in fname and fname.endswith('.tba')]
    if mapfile and mapfile[0]:
        with tarfile.extractfile(mapfile[0]) as mfile:
            content = mfile.read()
            return content and content.decode().strip() == 'Atlas 1.0'
    return False


def get_sets(tarfile, basedir):
    files = [fname
             for fname in tarfile.getnames()
             if fname.endswith('.set')]
    for fname in files:
        if os.path.isfile(os.path.join(basedir, fname)):
            yield fname
        else:
            tarred_fname = os.path.splitext(fname)[0] + '.tar'
            if os.path.isfile(os.path.join(basedir, tarred_fname)):
                yield tarred_fname
            else:
                print("missing %s and %s", fname, tarred_fname)
