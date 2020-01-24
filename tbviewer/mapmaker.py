#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2020 Karol Będkowski <Karol Będkowski@kntbk>
#
# Distributed under terms of the GPLv3 license.

"""Function for creating trekbuddy maps."""

import os
import os.path
import logging
import tarfile

from PIL import Image

_LOG = logging.getLogger(__name__)


def cut_map(filename, dst_dir, dst_name, tile_size=None, force=False):
    """Cut image into tiles and create set file/dir.

    :param filename: image filename
    :param dst_dir: destination directory
    :param tile_size: (tile width, tile_height), default=(256, 256)
    """
    img = Image.open(filename)
    img_width = img.width
    img_height = img.height
    tile_width, tile_height = tile_size or (256, 256)

    dst_name = os.path.splitext(dst_name)[0]

    img_dst_dir = os.path.join(dst_dir, "set")
    os.makedirs(img_dst_dir, exist_ok=True)

    existing_files = set() if force else set(os.listdir(img_dst_dir))

    img_names = []
    for x in range(0, img_width, tile_width):
        for y in range(0, img_height, tile_height):
            fname = f"{dst_name}_{x}_{y}.jpg"
            if fname in existing_files:
                _LOG.debug("skipping %s", fname)
                continue

            _LOG.debug("creating %s", fname)
            img_names.append(fname)
            simg = img.copy().crop((x, y, x + tile_width, y + tile_height))
            img_filepath = os.path.join(img_dst_dir, fname)
            simg.save(img_filepath, "JPEG")
            simg = None

    set_fname = dst_name + ".set"
    with open(os.path.join(dst_dir, set_fname), "tw") as fset:
        fset.write("\n".join(img_names))


def create_map(img_filename, map_content, dst_file, options=None):
    """Create trekbuddy map file.

    :param img_filename: map image file name
    :param map_content: content of .map file
    :param dst_file: destination .map file name
    :param options: map options
    """
    opt = {
        'tile_size': (256, 256),
        'create_tar': True,
        'force': False,
    }
    opt.update(options or {})
    dst_dir = os.path.dirname(dst_file)
    name = os.path.basename(dst_file)
    cut_map(img_filename, dst_dir, name, tile_size=opt['tile_size'],
            force=opt['force'])
    if map_content:
        with open(dst_file, "wt") as fmap:
            fmap.write(map_content)

    if opt['create_tar']:
        tar_fname = os.path.splitext(dst_file)[0] + ".tar"
        _LOG.info("creating %s", tar_fname)

        with tarfile.open(tar_fname, "w") as tar:
            tar.add(dst_file, os.path.basename(dst_file))

            set_fname = dst_file[:-3] + "set"
            tar.add(set_fname, os.path.basename(set_fname))

            for img_name in os.listdir(os.path.join(dst_dir, 'set')):
                tar.add(os.path.join(dst_dir, 'set', img_name),
                        os.path.join('set', img_name))
