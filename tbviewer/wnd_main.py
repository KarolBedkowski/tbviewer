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

        self._canvas_tiles_x = 10
        self._canvas_tiles_y = 8
        self._mapset = None
        self._tiles = {}

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
        self._canvas_img = None
        self._img = None
        self._sets = {}
        if fname:
            self._load(fname)
        self._tree.bind("<Button-1>", self._on_tree_click)

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
        self._img = []
        for iid, in self._sets.keys():
            self._tree.delete(iid)
        _LOG.info('Loading %s', fname)
        mapfile = map_loader.MapFile(fname)
        # check for atlas
        if mapfile.is_atlas():
            _LOG.info('loading atlas')
            album_dir = os.path.dirname(fname)
            for idx, set_ in enumerate(mapfile.get_sets()):
                iid = self._tree.insert('', idx, text=os.path.dirname(set_))
                self._sets[iid] = os.path.join(album_dir, set_)
        else:
            _LOG.info('loading map')
            self._load_set(fname)

    def _load_set(self, filename):
        self._mapset = mapset = map_loader.MapSet(filename)
        self._canvas.config(scrollregion=(0, 0, mapset.width, mapset.height)),
        self._draw_tiles()
#        for row, col, img in mapset.get_images():
#            self._canvas_img = self._canvas.create_image(
#                row, col, image=img, anchor=tk.NW, tag='img')

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

    def _draw_tiles(self):
        if not self._mapset:
            return
        tile_start_x = max(self._canvas.canvasx(0), 0) // 256
        tile_start_y = max(self._canvas.canvasy(0), 0) // 256
        new_tile_list = {}
        for x in range(self._canvas_tiles_x):
            tx = int((x + tile_start_x) * 256)
            for y in range(self._canvas_tiles_y):
                ty = int((y + tile_start_y) * 256)
                if (tx, ty) in self._tiles:
                    new_tile_list[(tx, ty)] = self._tiles[(tx, ty)]
                else:
                    try:
                        img = self._mapset.get_tile(tx, ty)
                        iid = self._canvas.create_image(tx, ty, image=img,
                                                        anchor=tk.NW)
                        new_tile_list[(tx, ty)] = iid, img
                    except:
                        pass
        self._tiles = new_tile_list
