# -*- coding: utf-8 -*-
""" Map loader routines.

Copyright (c) Karol Będkowski, 2015-2017

This file is part of tbviewer
Licence: GPLv2+
"""
import os.path
import collections
import tarfile
import logging

from PIL import ImageTk


__author__ = "Karol Będkowski"
__copyright__ = "Copyright (c) Karol Będkowski, 2015-2017"

_LOG = logging.getLogger(__name__)


class InvalidFileException(RuntimeError):
    pass


class MapMeta(object):
    """docstring for MapMeta"""
    def __init__(self):
        super(MapMeta, self).__init__()
        self.width = 0
        self.height = 0
        self.filename = None
        self._points = []
        self.lat_pix = 0
        self.lon_pix = 0
        self.min_lat = 0
        self.min_lon = 0

    def valid(self):
        return self.width and self.height

    def add_mmpll(self, point_id, lon, lat):
        if point_id != len(self._points) - 1:
            _LOG.warn("point of out order")
        self._points.append((lon, lat))

    def calculate(self):
        self.min_lon, self.min_lat = self._points[0]
        self.lat_pix = (self._points[3][1] - self._points[0][1])\
            / self.height
        self.lon_pix = (self._points[1][0] - self._points[0][0])\
            / self.width

    def xy2lonlat(self, x, y):
        """ Calculate lon & lat from position. """
        return (x * self.lon_pix + self.min_lon,
                y * self.lat_pix + self.min_lat)


def _parse_mmpll(line):
    fields = line.split(',')
    if len(fields) != 4:
        raise InvalidFileException("Wrong number of fields in MMPLL field %r"
                                   % line)
    _, point_id, lon, lat = [field.strip() for field in fields]
    try:
        point_id = int(point_id)
        lon = float(lon)
        lat = float(lat)
    except ValueError as err:
        raise InvalidFileException("Wrong MMPLL field %r; %s" % (line, err))
    return point_id, lon, lat


def parse_map(content):
    """ Parse content of .map file """
    content = [line.strip() for line in content]
    # OziExplorer Map Data File Version 2.2
    if content[0] != 'OziExplorer Map Data File Version 2.2':
        raise InvalidFileException("Wrong header %r" % content[0])

    result = MapMeta()
    result.filename = os.path.splitext(content[1])[0]
    for line in content[2:]:
        if line.startswith('IWH,Map Image Width/Height,'):
            result.width, result.height = map(int, line[27:].split(','))
            continue
        if line.startswith('MMPLL'):
            point_id, lon, lat = _parse_mmpll(line)
            result.add_mmpll(point_id, lon, lat)

    if not result.valid():
        raise InvalidFileException("missing width/height")

    result.calculate()
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
        self.map_data = None
        self._set_data = collections.defaultdict(dict)
        self._load_data()
        self.tile_width, self.tile_height = self._get_tile_size()

    @property
    def width(self):
        """ Whole map width. """
        return self.map_data.width

    @property
    def height(self):
        """ Whole map height. """
        return self.map_data.height

    def _get_tile_size(self):
        # get tile size - find minimal pos (x,y) > 0
        if len(self._set_data) == 1:
            width = self.map_data.width
        else:
            width = min(key for key in self._set_data.keys() if key > 0)
        for row in self._set_data.values():
            if len(row) == 1:
                height = self.map_data.height
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
            self.map_data = parse_map(mapfile.readlines())

        # find set files
        set_data = self._set_data
        setdirname = os.path.join(os.path.dirname(self.name), 'set')
        for ifile in os.listdir(setdirname):
            if ifile.endswith('.map') or ifile.endswith('.set') or \
                    '_' not in ifile:
                continue
            name = os.path.splitext(ifile)[0]
            names = name.split('_')
            y = names[-2]
            x = names[-1]
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
            self.map_data = parse_map(content)

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
