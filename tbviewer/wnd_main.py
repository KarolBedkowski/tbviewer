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


import tarfile
import logging
import os.path

import tkinter as tk
from tkinter import filedialog
from tkinter import ttk
from PIL import ImageTk

from . import map_loader

_LOG = logging.getLogger(__name__)


class WndMain(tk.Tk):
    def __init__(self, fname):
        tk.Tk.__init__(self)

        style = ttk.Style()
        style.theme_use("clam")

        self._build_menu()
        self.title("TBViewer")

        self._tree = ttk.Treeview(self)
        self._tree.grid(column=0, row=0, sticky=(tk.N, tk.S, tk.E))
        ttk.Separator(self, orient=tk.VERTICAL).grid(row=0, column=1,
                                                     sticky='ns')

        h = ttk.Scrollbar(self, orient=tk.HORIZONTAL)
        v = ttk.Scrollbar(self, orient=tk.VERTICAL)
        self._canvas = tk.Canvas(self, scrollregion=(0, 0, 1000, 1000),
                                 yscrollcommand=v.set, xscrollcommand=h.set)
        h['command'] = self._canvas.xview
        v['command'] = self._canvas.yview
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
        for iid, in self._sets.keys():
            self._tree.delete(iid)
        _LOG.info('Loading %s', fname)
        tfile = tarfile.open(fname, 'r')
        # check for atlas
        if map_loader.is_atlas(tfile):
            _LOG.info('loading atlas')
            sets = list(map_loader.get_sets(tfile, os.path.dirname(fname)))
            album_dir = os.path.dirname(fname)
            for idx, set_ in enumerate(sets):
                iid = self._tree.insert('', idx, text=os.path.dirname(set_))
                self._sets[iid] = os.path.join(album_dir, set_)
        else:
            _LOG.info('loading map')
            self._load_set('set/', tfile)

    def _load_set(self, set_path, tfile=None, fname=None):
        tfile = tfile or tarfile.open(fname, 'r')
        map_data, set_data = map_loader.load_tar(tfile)
        self._canvas.config(scrollregion=(0, 0, map_data['width'],
                                          map_data['height']))
        self._img = []
        for row, rows in set_data.items():
            for col, cell in rows.items():
                with tfile.extractfile(set_path + cell) as ffile:
                    img = ImageTk.PhotoImage(data=ffile.read())
                    self._img.append(img)
                    self._canvas_img = self._canvas.create_image(
                        row, col, image=img, anchor=tk.NW, tag='img')

    def _on_tree_click(self, event):
        item = self._tree.identify('item', event.x, event.y)
        if item:
            self._load_set("set/", fname=self._sets[item])
