# -*- coding: utf-8 -*-
""" Map loader routines.

Copyright (c) Karol Będkowski, 2015-2020

This file is part of tbviewer
Licence: GPLv2+
"""
import os.path
import collections
import tarfile
import logging

from PIL import ImageTk


__author__ = "Karol Będkowski"
__copyright__ = "Copyright (c) Karol Będkowski, 2015-2020"

_LOG = logging.getLogger(__name__)


class InvalidFileException(RuntimeError):
    pass


class TarredFS:
    def __init__(self, basefile):
        self._tar = tarfile.open(basefile)
        self.basedir = os.path.dirname(basefile)

    def close(self):
        self._tar.close()

    def get_file_content(self, path):
        return self.get_file_binary(path).decode('cp1250')

    def get_file_binary(self, path):
        with self._tar.extractfile(path) as f:
            return f.read()

    def list(self, path):
        for fname in self._listdir(path):
            yield fname.name

    def list_dirs(self, path):
        for member in self._listdir(path):
            if member.isdir():
                yield member.name[len(path):].lstrip('/')

    def list_files(self, path):
        for member in self._listdir(path):
            if member.isfile():
                yield member.name[len(path):].lstrip('/')

    def _listdir(self, path):
        if path and path[0] == '/':
            path = path[1:]
        if path and path[-1] != '/':
            path += '/'

        for member in self._tar.getmembers():
            if not member.name.startswith(path):
                continue
            stpath = member.name[len(path):]
            if '/' in stpath:  # subdirs
                continue
            yield member


class RealFS:
    def __init__(self, basepath):
        self._basepath = basepath
        self.basedir = basepath

    def close(self):
        pass

    def get_file_content(self, path):
        realpath = os.path.join(self._basepath, path)
        with open(realpath, 'r') as f:
            return f.read()

    def get_file_binary(self, path):
        realpath = os.path.join(self._basepath, path)
        with open(realpath, 'b') as f:
            return f.read()

    def list(self, path):
        realpath = os.path.join(self._basepath, path)
        yield from os.listdir(realpath)

    def list_files(self, path):
        realpath = os.path.join(self._basepath, path)
        for member in os.listdir(realpath):
            if os.path.isfile(os.path.join(realpath, member)):
                yield member

    def list_dirs(self, path):
        realpath = os.path.join(self._basepath, path)
        for member in os.listdir(realpath):
            if os.path.isdir(os.path.join(realpath, member)):
                yield member


class Atlas:
    def __init__(self, path):
        if path.endswith('.tba'):  # plain fs
            self._fs = RealFS(os.path.dirname(path))
        elif path.endswith('.tar'):  # compressed fs
            self._fs = TarredFS(path)

        self.layers = list(self._load_layers(self._fs.basedir))
        self.layers.sort()

    def close(self):
        self._fs.close()

    def _load_layers(self, path):
        for layer in self._fs.list_dirs(""):
            _LOG.debug("layer: %s", layer)
            maps = [
                (name, os.path.join(path, layer, name))
                for name in self._fs.list_dirs(layer)]
            yield layer, maps


class FakeAlbum:
    def __init__(self, path):
        self.layers = [("base", [(os.path.basename(path), path)])]

    def close(self):
        pass


def find_file_in_dir(path, ext):
    for fname in os.listdir(path):
        if fname.endswith(ext):
            return os.path.join(path, fname)
    return None


class Map:
    def __init__(self, path):
        self._fs = self._find_fs(path)
        self.map_data = self._load_map_meta()
        self.set_data = dict(self._load_set())
        self.tile_width, self.tile_height = self._find_tile_size()
        _LOG.debug("map: %s %r %r %r", self.map_data, self.set_data,
                   self.tile_width, self.tile_height)

    def _find_fs(self, path):
        if os.path.isfile(path):
            if path.endswith(".tar"):
                return TarredFS(path)
            if path.endswith(".map"):
                return RealFS(os.path.dirname(path))

        tar_file = find_file_in_dir(path, ".tar")
        if tar_file:
            return TarredFS(tar_file)

        map_file = find_file_in_dir(path, ".map")
        if map_file:
            return RealFS(os.path.dirname(map_file))

        return None

    def close(self):
        """Close map."""
        self._fs.close()

    @property
    def width(self):
        """Whole map width."""
        return self.map_data.width

    @property
    def height(self):
        """Whole map height."""
        return self.map_data.height

    def get_tile(self, x, y):
        """Get one tile from tar file."""
        name = self.set_data.get((x, y))
        if not name:
            _LOG.error("wrong tile pos: %d, %d", x, y)
            return None
        data = self._fs.get_file_binary(name)
        _LOG.debug('tile pos: %d, %d, size: %d', x, y, len(data))
        return ImageTk.PhotoImage(data=data)

    def _load_map_meta(self):
        # find map file
        map_filename = self._find_map_file()
        if not map_filename:
            return None
        map_conent = self._fs.get_file_content(map_filename).split('\r\n')
        return parse_map(map_conent)

    def _find_map_file(self):
        for name in self._fs.list(""):
            if name.endswith(".map"):
                _LOG.debug("found %s map file", name)
                return name
        _LOG.warn("no map file found")
        return None

    def _load_set(self):
        for name in self._fs.list_files("set/"):
            bname, ext = os.path.splitext(name)
            if ext.lower() not in ('.jpg', '.png', '.jpeg'):
                _LOG.warn("unknown file extension: %s", name)
            name_parts = bname.split('_')
            if len(name_parts) < 3:
                _LOG.warn("wrong file name: %s", bname)
                continue

            x, y = int(name_parts[-2]), int(name_parts[-1])
            yield (x, y), os.path.join('set', name)

    def _find_tile_size(self):
        tile_width = 8192
        tile_height = 8192
        for (x, y) in self.set_data:
            if y == 0 and tile_width > x and x > 0:
                tile_width = x

            if x == 0 and tile_height > y and y > 0:
                tile_height = y

        return tile_width, tile_height


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

    def __str__(self):
        return "<MapMeta {}>".format(", ".join(
            "{}={}".format(k, v)
            for k, v in self.__dict__.items()
            if k[0] != '_'
        ))

    def valid(self):
        return self.width and self.height

    def add_mmpll(self, point_id, lon, lat):
        if point_id != len(self._points) - 1:
            _LOG.warn("point of out order")
        self._points.append((lon, lat))

    def calculate(self):
        self.min_lon, self.min_lat = self._points[0]
        self.max_lon, self.max_lat = self._points[3]
        self.lat_pix = (self._points[3][1] - self._points[0][1])\
            / self.height
        self.lon_pix = (self._points[1][0] - self._points[0][0])\
            / self.width

    def xy2lonlat(self, x, y):
        """ Calculate lon & lat from position. """
        return _map_xy_lonlat(
            self._points[0], self._points[1],
            self._points[2], self._points[3],
            self.width, self.height,
            x, y)


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


def check_valid_atlas(tba_file):
    content = tba_file.read()
    if not content:
        return False
    if isinstance(content, bytes):
        content = content.decode()
    return content.strip() == 'Atlas 1.0'


def check_valid_map_file(map_file):
    content = map_file.read()
    if not content:
        return False
    if isinstance(content, bytes):
        content = content.decode()
    return content.startswith('OziExplorer Map Data File Version 2.2')


def check_file_type(file_name):
    _LOG.debug("check_file_type: %s", file_name)

    if file_name.endswith(".tba"):
        with open(file_name) as mfile:
            if check_valid_atlas(mfile):
                return 'atlas'
        return None

    if file_name.endswith(".map"):
        with open(file_name) as mfile:
            if check_valid_map_file(mfile):
                return 'map'

    if file_name.endswith(".tar"):
        with tarfile.open(file_name) as tfile:
            tar_content = tfile.getnames()
            _LOG.debug("check_valid_map_file: tar_content: %s", tar_content)
            tba_files = [fname for fname in tar_content
                         if fname.endswith('.tba')]
            if tba_files:
                with tfile.extractfile(tba_files[0]) as tbafile:
                    if check_valid_atlas(tbafile):
                        return 'tar-atlas'

            map_files = [fname for fname in tar_content
                         if fname.endswith(".map")]
            if map_files:
                with tfile.extractfile(map_files[0]) as map_file:
                    if check_valid_map_file(map_file):
                        return 'tar-map'

    return None


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
