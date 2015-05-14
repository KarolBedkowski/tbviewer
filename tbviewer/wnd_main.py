#!/usr/bin/python3
# -*- coding: utf-8 -*-
""" Main window.

Copyright (c) Karol Będkowski, 2015

This file is part of tbviewer
Licence: GPLv2+
"""

__author__ = "Karol Będkowski"
__copyright__ = "Copyright (c) Karol Będkowski, 2015"
__version__ = "2015-05-10"


import logging
import os.path
import time

import tkinter as tk
from tkinter import filedialog
from tkinter import ttk

from . import map_loader

_LOG = logging.getLogger(__name__)


class WndMain(tk.Tk):
    def __init__(self, fname):
        tk.Tk.__init__(self)

        style = ttk.Style()
        style.theme_use("clam")

        self._build_menu()
        self.title("TBViewer")

        self._mapset = None
        self._tiles = {}
        self._sets = {}

        self._tree = ttk.Treeview(self)
        self._tree.grid(column=0, row=0, sticky=(tk.N, tk.S, tk.E))
        ttk.Separator(self, orient=tk.VERTICAL).grid(row=0, column=1,
                                                     sticky='ns')

        self._scrollbar_h = h = ttk.Scrollbar(self, orient=tk.HORIZONTAL)
        self._scrollbar_v = v = ttk.Scrollbar(self, orient=tk.VERTICAL)
        self._canvas = tk.Canvas(self, scrollregion=(0, 0, 1000, 1000),
                                 yscrollcommand=v.set, xscrollcommand=h.set)
        h['command'] = self._move_scroll_h
        v['command'] = self._move_scroll_v
        ttk.Sizegrip(self).grid(column=3, row=1, sticky=(tk.S, tk.E))
        self._canvas.grid(column=2, row=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        h.grid(column=2, row=1, sticky=(tk.W, tk.E))
        v.grid(column=3, row=0, sticky=(tk.N, tk.S))
        self.grid_columnconfigure(2, weight=1)
        self.grid_rowconfigure(0, weight=1)
        if fname:
            self._load(fname)
        self._tree.bind("<Button-1>", self._on_tree_click)
        self._canvas.bind("<Configure>", self._draw_tiles)

    def onExit(self):
        self.quit()

    def _build_menu(self):
        menubar = tk.Menu(self)
        self.config(menu=menubar)
        file_menu = tk.Menu(menubar, tearoff=False)
        file_menu.add_command(label="Open", command=self._open_file)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.onExit)
        menubar.add_cascade(label="File", menu=file_menu)

    def _open_file(self):
        dlg = filedialog.FileDialog(self)
        fname = dlg.go(".", "*.tar")
        if fname:
            self._load(fname)

    def _load(self, fname):
        self._canvas.delete('img')
        for iid, in self._sets.keys():
            self._tree.delete(iid)
        _LOG.info('Loading %s', fname)
        mapfile = map_loader.MapFile(fname)
        # check for atlas
        if mapfile.is_atlas():
            _LOG.info('loading atlas')
            adirlen = len(os.path.dirname(fname)) + 1
            for idx, set_ in enumerate(sorted(mapfile.get_sets())):
                iid = self._tree.insert('', idx,
                                        text=os.path.dirname(set_)[adirlen:])
                self._sets[iid] = set_
                self._clear_tile_cache()
        else:
            _LOG.info('loading map')
            self._load_set(fname)

    def _load_set(self, filename):
        self._mapset = mapset = map_loader.MapSet(filename)
        self._canvas.config(scrollregion=(0, 0, mapset.width, mapset.height))
        self._clear_tile_cache()
        self._draw_tiles(True)

    def _on_tree_click(self, event):
        item = self._tree.identify('item', event.x, event.y)
        if item:
            self._load_set(self._sets[item])

    def _move_scroll_v(self, scroll, num, units=None):
        self._canvas.yview(scroll, num, units)
        self._draw_tiles()

    def _move_scroll_h(self, scroll, num, units=None):
        self._canvas.xview(scroll, num, units)
        self._draw_tiles()

    def _draw_tiles(self, clear=False):
        if not self._mapset:
            return
        tstart = time.time()
        canvas = self._canvas
        mapset_get_tile = self._mapset.get_tile
        tile_width = self._mapset.tile_width
        tile_height = self._mapset.tile_height
        tiles_x = (canvas.winfo_width() // tile_width) + 2
        tiles_y = (canvas.winfo_height() // tile_height) + 2
        tile_start_x = max(canvas.canvasx(0), 0) // tile_width
        tile_start_y = max(canvas.canvasy(0), 0) // tile_height
        new_tile_list = {}
        for x in range(tiles_x):
            tx = int((x + tile_start_x) * tile_width)
            for y in range(tiles_y):
                ty = int((y + tile_start_y) * tile_height)
                if (tx, ty) in self._tiles:
                    new_tile_list[(tx, ty)] = self._tiles[(tx, ty)]
                else:
                    try:
                        img = mapset_get_tile(tx, ty)
                        iid = canvas.create_image(
                            tx, ty, image=img, anchor=tk.NW)
                        new_tile_list[(tx, ty)] = iid, img
                    except:
                        pass
        for txty, (iid, _) in self._tiles.items():
            if txty not in new_tile_list:
                canvas.delete(iid)
        self._tiles = new_tile_list
        _LOG.debug("_draw_tiles in %s", time.time() - tstart)

    def _clear_tile_cache(self):
        for (iid, _) in self._tiles.values():
            self._canvas.delete(iid)
        self._tiles = {}
