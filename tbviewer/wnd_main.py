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

import tkinter as tk
from tkinter import filedialog
from tkinter import ttk
from PIL import ImageTk

from . import map_loader

assert tk


class WndMain(tk.Tk):
    def __init__(self):
        tk.Tk.__init__(self)

        style = ttk.Style()
        style.theme_use("clam")

        self._build_menu()
        self.title("TBViewer")
        h = ttk.Scrollbar(self, orient=tk.HORIZONTAL)
        v = ttk.Scrollbar(self, orient=tk.VERTICAL)
        self._canvas = tk.Canvas(self, scrollregion=(0, 0, 1000, 1000),
                                 yscrollcommand=v.set, xscrollcommand=h.set)
        h['command'] = self._canvas.xview
        v['command'] = self._canvas.yview
        ttk.Sizegrip(self).grid(column=1, row=1, sticky=(tk.S, tk.E))
        self._canvas.grid(column=0, row=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        h.grid(column=0, row=1, sticky=(tk.W, tk.E))
        v.grid(column=1, row=0, sticky=(tk.N, tk.S))
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._canvas_img = None
        self._img = None

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
        if fname is None:
            return
        self._canvas.delete('img')
        tfile = tarfile.open(fname, 'r')
        map_data, set_data = map_loader.load_tar(tfile)
        self._canvas.config(scrollregion=(0, 0, map_data['width'],
                                          map_data['height']))
        self._img = []
        for row, rows in set_data.items():
            for col, cell in rows.items():
                with tfile.extractfile('set/' + cell) as ffile:
                    img = ImageTk.PhotoImage(data=ffile.read())
                    self._img.append(img)
                    self._canvas_img = self._canvas.create_image(
                        row, col, image=img, anchor=tk.NW, tag='img')
