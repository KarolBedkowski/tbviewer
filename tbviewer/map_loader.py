# -*- coding: utf-8 -*-
""" Map loader routines.

Copyright (c) Karol Będkowski, 2015

This file is part of tbviewer
Licence: GPLv2+
"""

__author__ = "Karol Będkowski"
__copyright__ = "Copyright (c) Karol Będkowski, 2015"
__version__ = "2015-05-14"

import os.path
import collections
import tarfile
import logging

from PIL import ImageTk


_LOG = logging.getLogger(__name__)


class InvalidFileException(RuntimeError):
    pass


def parse_map(content):
    """ Parse content of .map file """
    content = [line.strip() for line in content]
    # OziExplorer Map Data File Version 2.2
    if content[0] != 'OziExplorer Map Data File Version 2.2':
        raise InvalidFileException("Wrong header %r" % content[0])
    result = {'filename': os.path.splitext(content[1])[0]}
    for line in content[2:]:
        if line.startswith('IWH,Map Image Width/Height,'):
            result['width'], result['height'] = map(int, line[27:].split(','))
    if 'width' not in result:
        raise InvalidFileException("missing width/height")
    return result


class MapFile(object):
    """ Map file - album or set. """
    def __init__(self, name):
        self.name = name
        self.directory = os.path.dirname(name)
        self._tarfile = tarfile.open(name, 'r')
        self.files = self._tarfile.getnames()

    def is_atlas(self):
        mapfile = [fname for fname in self.files
                   if fname.endswith('.tba')]
        if mapfile and mapfile[0]:
            with self._tarfile.extractfile(mapfile[0]) as mfile:
                content = mfile.read()
                return content and content.decode().strip() == 'Atlas 1.0'
        return False

    def get_sets(self):
        files = [fname for fname in self.files if fname.endswith('.map')]
        for fname in files:
            _LOG.debug("MapFile.get_sets checking %s", fname)
            fpath = _check_filename(self.directory, fname)
            if fpath:
                yield fname
                _LOG.debug("MapFile.get_sets found %s", fname)
                continue
            lfname = os.path.splitext(fname)[0] + '.tar'
            fpath = _check_filename(self.directory, lfname)
            _LOG.debug("MapFile.get_sets checking %s (%s)", lfname, fpath)
            if fpath:
                yield fpath
                _LOG.debug("MapFile.get_sets found %s", fname)
                continue
            # is any tar file there?
            tardir = os.path.join(self.directory, os.path.dirname(fname))
            tars = [fname for fname in os.listdir(tardir)
                    if fname.endswith('.tar')]
            if len(tars) == 1:
                yield os.path.join(tardir, tars[0])
                _LOG.debug("MapFile.get_sets found %s/%s", tardir, tars[0])
                continue

            _LOG.warn("MapFile.get_sets missing %s", fname)


def _check_filename(dirname, filename):
    fpath = os.path.join(dirname, filename)
    if os.path.isfile(fpath):
        return fpath
    fpath = os.path.join(dirname, filename.lower())
    if os.path.isfile(fpath):
        return fpath
    return None


class MapSet(object):
    def __init__(self, name):
        _LOG.info("MapSet %r", name)
        self.name = name
        self._map_data = {}
        self._set_data = collections.defaultdict(dict)
        self._load_data()
        self.tile_width, self.tile_height = self._get_tile_size()

    @property
    def width(self):
        """ Whole map width. """
        return self._map_data['width']

    @property
    def height(self):
        """ Whole map height. """
        return self._map_data['height']

    def _get_tile_size(self):
        # get tile size - find minimal pos (x,y) > 0
        if len(self._set_data) == 1:
            width = self._map_data['width']
        else:
            width = min(key for key in self._set_data.keys() if key > 0)
        for row in self._set_data.values():
            if len(row) == 1:
                height = self._map_data['height']
            else:
                height = min(key for key in row.keys() if key > 0)
            return width, height

    def _load_data(self):
        _LOG.debug("MapSet._load_data %s", self.name)
        if os.path.isdir(self.name):
            map_file = [fname for fname in os.listdir(self.name)
                        if fname.endswith('.map')
                        and os.path.isfile(os.path.join(self.name, fname))]
            if not map_file:
                raise InvalidFileException(".map file not found")
            self.name = os.path.join(self.name, map_file[0])

        _LOG.debug("MapSet._load_data mapfile=%s", self.name)

        if not os.path.isfile(self.name) or not self.name.endswith('.map'):
            raise InvalidFileException("invalid file - should be .map")

        with open(self.name) as mapfile:
            self._map_data = parse_map(mapfile.readlines())

        # find set files
        set_data = self._set_data
        setdirname = os.path.join(os.path.dirname(self.name), 'set')
        for ifile in os.listdir(setdirname):
            if ifile.endswith('.map') or ifile.endswith('.set') or \
                    '_' not in ifile:
                continue
            name = os.path.splitext(ifile)[0]
            dummy, y, x = name.split('_')
            set_data[int(y)][int(x)] = os.path.join(setdirname, ifile)

    def get_tile(self, x, y):
        """ Get one tile from tar file. """
        name = self._set_data[x][y]
        return ImageTk.PhotoImage(file=name)


class MapSetTarred(MapSet):
    """ Single map. """
    def __init__(self, name):
        self._tarfile = None
        MapSet.__init__(self, name)

    def get_tile(self, x, y):
        """ Get one tile from tar file. """
        name = self._set_data[x][y]
        with self._tarfile.extractfile(name) as ffile:
            return ImageTk.PhotoImage(data=ffile.read())

    def _load_data(self):
        _LOG.debug("MapSetTarred._load_data %s", self.name)
        self._tarfile = tarfile.open(self.name, 'r')
        files = self._tarfile.getnames()
        # find map in root
        mapfile = [fname for fname in files
                   if fname.endswith('.map')]
        if not mapfile:
            raise InvalidFileException('map file not found')
        mapfile = mapfile[0]
        _LOG.debug("MapSetTarred._load_data mapfile: %s", mapfile)
        # load map
        with self._tarfile.extractfile(mapfile) as mfile:
            content = [line.decode('cp1250') for line in mfile.readlines()]
            self._map_data = parse_map(content)

        # find set files
        set_data = self._set_data
        for ifile in files:
            if ifile.endswith('.map') or ifile.endswith('.set') or \
                    '_' not in ifile:
                continue
            name = os.path.splitext(ifile)[0]
            itms = name.split('_')
            y = itms[-2]
            x = itms[-1]
            set_data[int(y)][int(x)] = ifile
