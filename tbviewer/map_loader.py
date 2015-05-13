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
import tarfile
import logging

from PIL import ImageTk


_LOG = logging.getLogger(__name__)


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
    # load map
    map_data = None
    with tarfile.extractfile(mapfile) as mfile:
        content = mfile.readlines()
        map_data = parse_map(content)

    # find set file
    set_data = collections.defaultdict(dict)
    for ifile in files:
        if ifile.endswith('.map') or ifile.endswith('.set'):
            continue
        name = os.path.splitext(ifile)[0]
        dummy, y, x = name.split('_')
        y = int(y)
        x = int(x)
        set_data[y][x] = ifile

    return map_data, set_data


class MapFile:
    def __init__(self, name):
        self.name = name
        self.directory = os.path.dirname(name)
        self._tarfile = tarfile.open(name, 'r')
        self.files = self._tarfile.getnames()

    def is_atlas(self):
        mapfile = [fname for fname in self.files
                if '/' not in fname and fname.endswith('.tba')]
        if mapfile and mapfile[0]:
            with self._tarfile.extractfile(mapfile[0]) as mfile:
                content = mfile.read()
                return content and content.decode().strip() == 'Atlas 1.0'
        return False

    def get_sets(self):
        files = [fname for fname in self.files if fname.endswith('.map')]
        for fname in files:
            if os.path.isfile(os.path.join(self.directory, fname)):
                yield fname
            else:
                tarred_fname = os.path.splitext(fname)[0] + '.tar'
                if os.path.isfile(os.path.join(self.directory, tarred_fname)):
                    yield tarred_fname
                else:
                    print("missing %s and %s", fname, tarred_fname)


class MapSet:
    def __init__(self, name):
        _LOG.info("MapSet %s", name)
        self._name = name
        self._tarfile = tarfile.open(name, 'r')
        self._map_data, self._set_data = load_tar(self._tarfile)

    @property
    def width(self):
        return self._map_data['width']

    @property
    def height(self):
        return self._map_data['height']

    def get_images(self):
        for row, rows in self._set_data.items():
            for col, cell in rows.items():
                with self._tarfile.extractfile(cell) as ffile:
                    img = ImageTk.PhotoImage(data=ffile.read())
                    yield row, col, img
