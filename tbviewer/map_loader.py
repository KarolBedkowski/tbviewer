# -*- coding: utf-8 -*-
#
# Copyright © Karol Będkowski, 2015-2020
#
# This file is part of tbviewer
# Distributed under terms of the GPLv3 license.

"""Map loader."""

import os.path
import collections
import tarfile
import logging
import io

from PIL import ImageTk, Image

from . import mapfile
from .errors import InvalidFileException

_LOG = logging.getLogger(__name__)


class _TarredFS:
    def __init__(self, basefile):
        self._tar = tarfile.open(basefile)

    def close(self):
        self._tar.close()

    def get_file_content(self, path):
        path = path.replace('\\', '/')
        return self.get_file_binary(path).decode('cp1250')

    def get_file_binary(self, path):
        path = path.replace('\\', '/')
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
        path = path.replace('\\', '/')
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


class _RealFS:
    def __init__(self, basepath):
        self._basepath = basepath

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
    """Real Trekbuddy atlas representation."""

    def __init__(self, path):
        if path.endswith('.tba'):  # plain fs
            self._fs = _RealFS(os.path.dirname(path))
        elif path.endswith('.tar'):  # compressed fs
            self._fs = _TarredFS(path)

        basedir = os.path.dirname(path)
        self.layers = sorted(self._load_layers(basedir))

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
    """Fake album representation, i.e. only one map."""

    def __init__(self, path):
        self.layers = [("base", [(os.path.basename(path), path)])]

    def close(self):
        pass


def _find_file_in_dir(path, ext):
    for fname in os.listdir(path):
        if fname.endswith(ext):
            return os.path.join(path, fname)
    return None


class Map:
    """Trekbuddy map representation."""

    def __init__(self, path):
        self._fs = self._find_fs(path)
        self.map_data = self._load_map_meta()
        self.set_data = dict(self._load_set())
        self.tile_width, self.tile_height = self._find_tile_size()
        _LOG.debug("map: deta=%s files=%r t-width=%r t-height=%r",
                   self.map_data, len(self.set_data), self.tile_width,
                   self.tile_height)

    def _find_fs(self, path):
        if os.path.isfile(path):
            if path.endswith(".tar"):
                return _TarredFS(path)
            if path.endswith(".map"):
                return _RealFS(os.path.dirname(path))

        tar_file = _find_file_in_dir(path, ".tar")
        if tar_file:
            return _TarredFS(tar_file)

        map_file = _find_file_in_dir(path, ".map")
        if map_file:
            return _RealFS(os.path.dirname(map_file))

        return None

    def close(self):
        """Close map."""
        self._fs.close()

    @property
    def width(self):
        """Whole map width."""
        return self.map_data.image_width

    @property
    def height(self):
        """Whole map height."""
        return self.map_data.image_height

    def get_tile(self, x, y, scale=1):
        """Get one tile from tar file."""
        name = self.set_data.get((x, y))
        if not name:
            if x < self.width and y < self.height:
                _LOG.error("wrong tile pos: %d, %d", x, y)
            return None
        data = self._fs.get_file_binary(name)
        if scale == 1:
            return ImageTk.PhotoImage(data=data)
        image = Image.open(io.BytesIO(data))
        image = image.resize(
            (int(image.width * scale), int(image.height * scale)),
            Image.ANTIALIAS)
        return ImageTk.PhotoImage(image)

    def _load_map_meta(self):
        # find map file
        map_filename = self._find_map_file()
        if not map_filename:
            return None
        map_conent = self._fs.get_file_content(map_filename)
        map_file = mapfile.MapFile()
        map_file.parse_map(map_conent)
        return map_file

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
        tile_width = 9999999
        tile_height = 9999999
        for (x, y) in self.set_data:
            if y == 0 and tile_width > x and x > 0:
                tile_width = x

            if x == 0 and tile_height > y and y > 0:
                tile_height = y

        if tile_width == 9999999 or tile_height == 9999999:
            raise InvalidFileException("Wrong set - missing files")

        return tile_width, tile_height


def _check_valid_atlas(tba_file):
    content = tba_file.read()
    if not content:
        return False
    if isinstance(content, bytes):
        content = content.decode()
    return content.strip() == 'Atlas 1.0'


def _check_valid_map_file(map_file):
    content = map_file.read()
    if not content:
        return False
    if isinstance(content, bytes):
        content = content.decode()
    return content.startswith('OziExplorer Map Data File Version 2.2')


def check_file_type(file_name):
    """Check what type of atlas/map is given file."""
    _LOG.debug("check_file_type: %s", file_name)

    if file_name.endswith(".tba"):
        with open(file_name) as mfile:
            if _check_valid_atlas(mfile):
                return 'atlas'
        return None

    if file_name.endswith(".map"):
        with open(file_name) as mfile:
            if _check_valid_map_file(mfile):
                return 'map'

    if file_name.endswith(".tar"):
        with tarfile.open(file_name) as tfile:
            tar_content = tfile.getnames()
            tba_files = [fname for fname in tar_content
                         if fname.endswith('.tba')]
            if tba_files:
                with tfile.extractfile(tba_files[0]) as tbafile:
                    if _check_valid_atlas(tbafile):
                        return 'tar-atlas'

            map_files = [fname for fname in tar_content
                         if fname.endswith(".map")]
            if map_files:
                with tfile.extractfile(map_files[0]) as map_file:
                    if _check_valid_map_file(map_file):
                        return 'tar-map'

    return None
