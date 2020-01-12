#!/usr/bin/python3
# -*- coding: utf-8 -*-
""" Main window.

Copyright (c) Karol Będkowski, 2015-2020

This file is part of tbviewer
Licence: GPLv2+
"""

import logging
import os.path
import time
import locale
import math

import tkinter as tk
from tkinter import filedialog
from tkinter import messagebox
from tkinter import ttk

from . import map_loader


__author__ = "Karol Będkowski"
__copyright__ = "Copyright (c) Karol Będkowski, 2015-2020"

_LOG = logging.getLogger(__name__)


class WndMain(tk.Tk):
    def __init__(self, fname):
        tk.Tk.__init__(self)

        style = ttk.Style()
        style.theme_use("clam")

        self._build_menu()
        self.title("TBViewer")

        self._tb_atlas = None
        self._current_map = None
        self._tiles = {}
        self._tb_maps = {}
        self._last_dir = "."

        self._tree = ttk.Treeview(self)
        self._tree.grid(column=0, row=0, sticky=tk.NSEW)
        ttk.Separator(self, orient=tk.VERTICAL).grid(row=0, column=1,
                                                     sticky=tk.NS)

        self._scrollbar_h = h = ttk.Scrollbar(self, orient=tk.HORIZONTAL)
        self._scrollbar_v = v = ttk.Scrollbar(self, orient=tk.VERTICAL)
        self._canvas = tk.Canvas(self, scrollregion=(0, 0, 1000, 1000),
                                 yscrollcommand=v.set, xscrollcommand=h.set)
        h['command'] = self._move_scroll_h
        v['command'] = self._move_scroll_v
        ttk.Sizegrip(self).grid(column=3, row=2, sticky=tk.SE)

        self._canvas.grid(column=2, row=0, sticky=tk.NSEW)
        h.grid(column=2, row=1, sticky=tk.EW)
        v.grid(column=3, row=0, sticky=tk.NS)
        self.grid_columnconfigure(2, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._status = tk.Label(self, text="", bd=1, relief=tk.SUNKEN,
                                anchor=tk.W)
        self._status.grid(column=0, row=2, columnspan=3, sticky=tk.EW)

        if fname:
            self._load(fname)

        self._tree.bind("<Button-1>", self._on_tree_click)
        self._canvas.bind("<Configure>", self._draw_tiles)
        self._canvas.bind("<ButtonPress-1>", self._scroll_start)
        self._canvas.bind("<B1-Motion>", self._scroll_move)
        self._canvas.bind('<Motion>', self._canvas_mouse_motion)

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
        fname = dlg.go(self._last_dir, "*.*")
        if fname:
            self._load(fname)
            self._last_dir = os.path.dirname(fname)

    def _load(self, fname):
        self._canvas.delete('img')
        for iid in self._tb_maps.keys():
            try:
                self._tree.delete(iid)
            finally:
                pass

        if self._tb_atlas:
            self._tb_atlas.close()
            self._tb_atlas = None
        if self._current_map:
            self._current_map.close()
            self._current_map = None

        self._tb_maps = {}
        self._clear_tile_cache()

        file_type = map_loader.check_file_type(fname)
        _LOG.info('Loading %s, %r', fname, file_type)
        if file_type in ('atlas', 'tar-atlas'):
            self._tb_atlas = map_loader.Atlas(fname)
        elif file_type in ('map', 'tar-map'):
            self._tb_atlas = map_loader.FakeAlbum(fname)
        else:
            messagebox.showerror(
                "Error loading file",
                "Invalid file - should be .map or .tar or .tba")
            return

        idx = 0
        for layer, maps in self._tb_atlas.layers:
            for map_name, map_path in maps:
                _LOG.debug("tree ins: %s %s %s", layer, map_name, map_path)
                iid = self._tree.insert('', idx, text=layer + ":" + map_name)
                self._tb_maps[iid] = map_path
                idx += 1

    def _load_map(self, filename):
        _LOG.info("_load_map %s", filename)
        self._current_map = map_loader.Map(filename)
        self._canvas.config(scrollregion=(0, 0, self._current_map.width,
                                          self._current_map.height))
        self._clear_tile_cache()
        self._draw_tiles(True)

    def _on_tree_click(self, event):
        item = self._tree.identify('item', event.x, event.y)
        if item:
            self._load_map(self._tb_maps[item])

    def _move_scroll_v(self, scroll, num, units=None):
        self._canvas.yview(scroll, num, units)
        self._draw_tiles()

    def _move_scroll_h(self, scroll, num, units=None):
        self._canvas.xview(scroll, num, units)
        self._draw_tiles()

    def _scroll_start(self, event):
        self._canvas.scan_mark(event.x, event.y)
        self._draw_tiles()

    def _scroll_move(self, event):
        self._canvas.scan_dragto(event.x, event.y, gain=1)
        self._draw_tiles()

    def _canvas_mouse_motion(self, event):
        if not self._current_map:
            self._status.config(text='')
            self._status.update_idletasks()
            return
        x = self._canvas.canvasx(event.x)
        y = self._canvas.canvasy(event.y)
        lon, lat = self._current_map.map_data.xy2lonlat(x, y)
        self._status.config(text=_format_degree(lon) + " " +
                            _format_degree(lat, True))
        self._status.update_idletasks()

    def _draw_tiles(self, clear=False):
        if not self._current_map:
            return
        tstart = time.time()
        canvas = self._canvas
        mapset_get_tile = self._current_map.get_tile
        tile_width = self._current_map.tile_width
        tile_height = self._current_map.tile_height
        tile_start_x = int(
            (max(canvas.canvasx(0), 0) // tile_width) * tile_width)
        tile_start_y = int(
            (max(canvas.canvasy(0), 0) // tile_height) * tile_height)
        tiles_x = int(tile_start_x
                      + ((canvas.winfo_width() // tile_width) + 2)
                      * tile_width)
        tiles_y = int(tile_start_y
                      + ((canvas.winfo_height() // tile_height) + 2)
                      * tile_height)
        new_tile_list = {}
        for tx in range(tile_start_x, tiles_x, tile_width):
            for ty in range(tile_start_y, tiles_y, tile_height):
                iidimg = self._tiles.get((tx, ty))
                if iidimg:
                    new_tile_list[(tx, ty)] = iidimg
                else:
                    img = mapset_get_tile(tx, ty)
                    if img:
                        iid = canvas.create_image(
                            tx, ty, image=img, anchor=tk.NW)
                        new_tile_list[(tx, ty)] = iid, img

        # remove unused tiles
        for txty, (iid, _) in self._tiles.items():
            if txty not in new_tile_list:
                canvas.delete(iid)
        self._tiles = new_tile_list
        _LOG.debug("_draw_tiles in %s", time.time() - tstart)

    def _clear_tile_cache(self):
        for (iid, _) in self._tiles.values():
            self._canvas.delete(iid)
        self._tiles = {}


def _format_degree(degree, latitude=True):
    lit = ["NS", "EW"][0 if latitude else 1][0 if degree > 0 else 1]
    degree = abs(degree)
    mint, stop = math.modf(degree)
    sec, mint = math.modf(mint * 60)
    return "%d %d' %s'' %s" % (stop, mint,
                               locale.format('%0.2f', sec * 60), lit)
