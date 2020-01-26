#!/usr/bin/python3
# -*- coding: utf-8 -*-
# Copyright © Karol Będkowski, 2015-2020
#
# This file is part of tbviewer
# Distributed under terms of the GPLv3 license.

"""Viewer main window."""

import logging
import os.path
import time
import locale
import math

import tkinter as tk
from tkinter import filedialog
from tkinter import messagebox
from tkinter import ttk
from tkinter import tix

from . import map_loader
from . import formatting
from . import tkutils
from .errors import InvalidFileException


_LOG = logging.getLogger(__name__)


class WndViewer(tk.Tk):
    """Main viewer window."""

    def __init__(self, fname):
        tk.Tk.__init__(self)

        style = ttk.Style()
        style.theme_use("clam")

        self._build_menu()
        self.title("TBViewer")

        self._busy_manager = tkutils.BusyManager(self)
        self._tb_atlas = None
        # current map image
        self._map_image = None
        self._tiles = {}
        self._last_dir = "."
        # map zoom; scale = 2^zoom
        self._zoom = 0

        self.grid_columnconfigure(2, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._tree = ttk.Treeview(self)
        self._tree.grid(column=0, row=0, sticky=tk.NSEW)
        ttk.Separator(self, orient=tk.VERTICAL).grid(row=0, column=1,
                                                     sticky=tk.NS)

        h = ttk.Scrollbar(self, orient=tk.HORIZONTAL)
        h['command'] = self._move_scroll_h
        h.grid(column=2, row=1, sticky=tk.EW)

        v = ttk.Scrollbar(self, orient=tk.VERTICAL)
        v['command'] = self._move_scroll_v
        v.grid(column=3, row=0, sticky=tk.NS)

        self._canvas = tk.Canvas(self, scrollregion=(0, 0, 1000, 1000),
                                 yscrollcommand=v.set, xscrollcommand=h.set,
                                 relief=tk.SUNKEN)
        self._canvas.grid(column=2, row=0, sticky=tk.NSEW)

        self._create_status_bar(self).grid(column=0, columnspan=3, row=2,
                                           sticky=tk.EW)
        ttk.Sizegrip(self).grid(column=3, row=2, sticky=tk.SE)

        if fname:
            self._load(fname)

        self._tree.bind("<Button-1>", self._on_tree_click)
        self._canvas.bind("<Configure>", self._draw_tiles)
        self._canvas.bind("<ButtonPress-1>", self._scroll_start)
        self._canvas.bind("<B1-Motion>", self._scroll_move)
        self._canvas.bind('<Motion>', self._canvas_mouse_motion)
        # with Windows OS
        self._canvas.bind("<MouseWheel>", self._canvas_mouse_wheel)
        # with Linux OS
        self._canvas.bind("<Button-4>", self._canvas_mouse_wheel)
        self._canvas.bind("<Button-5>", self._canvas_mouse_wheel)

        self.geometry("1024x768")
        self.lift()

    def _create_status_bar(self, parent):
        frame = tk.Frame(parent)
        frame.grid_columnconfigure(3, weight=1)
        self._status_lon = tk.Label(frame, text="", bd=1, relief=tk.SUNKEN)
        self._status_lon.grid(column=0, row=0, ipadx=3)
        self._status_lat = tk.Label(frame, text="", bd=1, relief=tk.SUNKEN)
        self._status_lat.grid(column=1, row=0, ipadx=3)
        self._status_scale = tk.Label(frame, text="", bd=1, relief=tk.SUNKEN)
        self._status_scale.grid(column=2, row=0, ipadx=3)
        self._status_text = tk.Label(frame, text="", bd=1, anchor=tk.E)
        self._status_text.grid(column=3, row=0, ipadx=3, sticky=tk.W)
        return frame

    def _build_menu(self):
        menubar = tk.Menu(self)
        self.config(menu=menubar)
        file_menu = tk.Menu(menubar, tearoff=False)
        file_menu.add_command(label="Open...", command=self._open_file)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.quit)
        menubar.add_cascade(label="File", menu=file_menu)

    def _open_file(self):
        fname = filedialog.askopenfilename(
            parent=self,
            filetypes=[("Supported files", ".tba .tar .map"),
                       ("All files", "*.*")],
            initialdir=self._last_dir)
        if fname:
            self._load(fname)
            self._last_dir = os.path.dirname(fname)
        self.focus_set()

    def _load(self, fname):
        self._status_text.config(text=f"Loading {fname}...")
        self._status_text.update_idletasks()
        self._canvas.delete('img')
        for iid in self._tree.get_children():
            self._tree.delete(iid)

        if self._tb_atlas:
            self._tb_atlas.close()
            self._tb_atlas = None
        if self._map_image:
            self._map_image.close()
            self._map_image = None

        self._clear_tile_cache()
        self._busy_manager.busy()
        self.update()

        try:
            file_type = map_loader.check_file_type(fname)
        except IOError as err:
            self._busy_manager.notbusy()
            messagebox.showerror("Error loading file", f"Read file {err}")
            self._status_text.config(text="Load error...")
            return

        _LOG.info('Loading %s, %r', fname, file_type)
        if file_type in ('atlas', 'tar-atlas'):
            self._tb_atlas = map_loader.Atlas(fname)
        elif file_type in ('map', 'tar-map'):
            self._tb_atlas = map_loader.FakeAlbum(fname)
        else:
            self._busy_manager.notbusy()
            messagebox.showerror(
                "Error loading file",
                "Invalid file - should be .map or .tar or .tba")
            self._status_text.config(text="Load error...")
            return

        idx = 0
        for layer, maps in self._tb_atlas.layers:
            parent = self._tree.insert('', idx, text=layer, open=True)
            idx += 1

            for map_name, map_path in maps:
                _LOG.debug("tree ins: %s %s %s", layer, map_name, map_path)
                self._tree.insert(parent, idx, text=map_name, tags=map_path)
                idx += 1

        # select first map
        tree_layers = self._tree.get_children()
        if tree_layers:
            tree_maps = self._tree.get_children(tree_layers[0])
            if tree_maps:
                self._tree.selection_set(tree_maps[0])
                self._on_tree_click(None, item=tree_maps[0])
        self._status_text.config(text="")
        self._busy_manager.notbusy()

    def _load_map(self, filename):
        self._busy_manager.busy()
        self.update()
        _LOG.info("_load_map %s", filename)
        if self._map_image:
            self._map_image = None

        try:
            self._map_image = map_loader.Map(filename)
            self._zoom = 0
            self._canvas.config(scrollregion=(0, 0, self._map_image.width,
                                              self._map_image.height))
        except InvalidFileException as err:
            messagebox.showerror("Error loading file",
                                 f"Invalid file: {err}")
        except IOError as err:
            messagebox.showerror("Error loading file",
                                 f"Open file error: {err}")
        self._clear_tile_cache()
        self._draw_tiles(True)
        self._busy_manager.notbusy()

    def _on_tree_click(self, event, item=None):
        item = item or self._tree.identify('item', event.x, event.y)
        map_path = self._tree.item(item, "tags")
        if map_path and map_path[0]:
            self._load_map(map_path[0])

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
        lat_txt = lon_txt = ""
        scale = 2 ** self._zoom
        if self._map_image:
            x = self._canvas.canvasx(event.x) / scale
            y = self._canvas.canvasy(event.y) / scale
            lat, lon = self._map_image.map_data.xy2latlon(x, y)
            lat_txt = formatting.format_pos(lat)
            lon_txt = formatting.format_pos(lon, True)
        self._status_lat.config(text=lat_txt)
        self._status_lon.config(text=lon_txt)
        self._status_lat.update_idletasks()
        self._status_lon.update_idletasks()
        self._status_scale.config(text=f"{scale:0.2f}x")

    def _canvas_mouse_wheel(self, event):
        if (event.num == 5 or event.delta == -120) and self._zoom > -5:
            self._zoom -= 1
        elif (event.num == 4 or event.delta == 120) and self._zoom < 5:
            self._zoom += 1
        self._clear_tile_cache()

        scale = 2.0 ** self._zoom
        map_width = int(self._map_image.width * scale)
        map_height = int(self._map_image.height * scale)
        self._canvas.config(scrollregion=(0, 0, map_width, map_height))
        self._draw_tiles(True)
        # refresh status
        self._canvas_mouse_motion(event)

    def _draw_tiles(self, clear=False):
        if not self._map_image:
            return
        canvas = self._canvas
        scale = 2.0 ** self._zoom
        mapset_get_tile = self._map_image.get_tile
        tile_width = self._map_image.tile_width
        tile_height = self._map_image.tile_height
        scaled_tile_width = int(tile_width * scale)
        scaled_tile_height = int(tile_height * scale)
        # canvas visible area
        visible_x0 = max(canvas.canvasx(0), 0)
        visible_y0 = max(canvas.canvasy(0), 0)
        visible_x1 = canvas.winfo_width()
        visible_y1 = canvas.winfo_height()

        tile_start_x = int(max(visible_x0 // scaled_tile_width, 0))
        tile_start_y = int(max(visible_y0 // scaled_tile_height, 0))
        tiles_x = int(visible_x1 // scaled_tile_width) + 2
        tiles_y = int(visible_y1 // scaled_tile_height) + 2

        new_tile_list = {}
        for txi in range(tile_start_x, tile_start_x + tiles_x):
            tx = tile_width * txi
            for tyi in range(tile_start_y, tile_start_y + tiles_y):
                ty = tile_height * tyi
                iidimg = self._tiles.get((tx, ty))
                if iidimg:
                    new_tile_list[(tx, ty)] = iidimg
                    continue

                img = mapset_get_tile(tx, ty, scale)
                if img:
                    iid = canvas.create_image(tx * scale, ty * scale,
                                              image=img, anchor=tk.NW)
                    new_tile_list[(tx, ty)] = iid, img

        # remove unused tiles
        for txty, (iid, _) in self._tiles.items():
            if txty not in new_tile_list:
                canvas.delete(iid)
        self._tiles = new_tile_list

    def _clear_tile_cache(self):
        for (iid, _) in self._tiles.values():
            self._canvas.delete(iid)
        self._tiles.clear()
