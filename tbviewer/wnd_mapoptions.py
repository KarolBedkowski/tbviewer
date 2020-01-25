#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright (c) Karol Będkowski, 2015-2020
#
# This file is part of tbviewer
# Distributed under terms of the GPLv3 license.

"""Mapmaker options dialog."""

import os.path

import tkinter as tk
from tkinter import filedialog


class MapOptionsDialog(tk.Toplevel):
    """Dialog with options for new trekbuddy map."""

    _opts = {
        'tile_size': (256, 256),
        'create_tar': True,
        'force': False,
        'filename': "",
        'format': "JPEG",
        'jpeg_quality': 80,
        'png_compression': 'optimized',
        'png_palette': 'RGB',
    }

    def __init__(self, parent, last_dir, last_map_file, options=None):
        """Create dialog.

        :param parent: parent widget
        """
        tk.Toplevel.__init__(self, parent, borderwidth=5)
        self.transient(parent)
        self.options = MapOptionsDialog._opts.copy()
        if last_map_file:
            self.options['filename'] = last_map_file
        if options:
            self.options.update(options)

        self.last_dir = last_dir
        self.result = False

        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)

        tk.Label(self, text="Tile width").grid(row=0, column=0, sticky=tk.W)
        self._var_tile_w = tk.IntVar()
        self._var_tile_w.set(self.options['tile_size'][0])
        tk.Entry(self, textvariable=self._var_tile_w).grid(
            row=0, column=1, sticky=tk.W)

        tk.Label(self, text="Tile height").grid(row=1, column=0, sticky=tk.W)
        self._var_tile_h = tk.IntVar()
        self._var_tile_h.set(self.options['tile_size'][1])
        tk.Entry(self, textvariable=self._var_tile_w).grid(
            row=1, column=1, sticky=tk.W)

        tk.Label(self, text="Format").grid(row=2, column=0, sticky=tk.W)
        self._var_format = tk.StringVar()
        self._var_format.set(self.options['format'])
        tk.OptionMenu(self, self._var_format, 'JPEG', 'PNG').grid(
            row=2, column=1, sticky=tk.W)

        tk.Label(self, text="JPEG quality (0-100)").grid(row=3, column=0,
                                                         sticky=tk.W)
        self._var_jpg_quality = tk.IntVar()
        self._var_jpg_quality.set(self.options['jpeg_quality'])
        tk.Entry(self, textvariable=self._var_jpg_quality, width=3).grid(
            row=3, column=1, sticky=tk.W)

        tk.Label(self, text="PNG compression").grid(row=4, column=0,
                                                    sticky=tk.W)
        self._var_png_comp = tk.StringVar()
        self._var_png_comp.set(self.options['png_compression'])
        tk.OptionMenu(self, self._var_png_comp, '0', '2', '4', '6', '8', '9',
                      'optimized').grid(row=4, column=1, sticky=tk.W)

        tk.Label(self, text="PNG palette").grid(row=5, column=0,
                                                sticky=tk.W)
        self._var_png_palette = tk.StringVar()
        self._var_png_palette.set(self.options['png_palette'])
        tk.OptionMenu(self, self._var_png_palette, 'RGB', '256c')\
            .grid(row=5, column=1, sticky=tk.W)

        self._var_tar = tk.BooleanVar()
        self._var_tar.set(self.options['create_tar'])
        tk.Checkbutton(self, text="Create tar file", variable=self._var_tar)\
            .grid(row=6, columnspan=2, column=0, sticky=tk.W)

        self._var_force = tk.BooleanVar()
        self._var_force.set(self.options['force'])
        tk.Checkbutton(self, text="Force create all tiles",
                       variable=self._var_force)\
            .grid(row=7, columnspan=2, column=0, sticky=tk.W)

        tk.Label(self, text="Map file name").grid(column=0, row=8, sticky=tk.W)
        sfr = tk.Frame(self, pady=10)
        sfr.grid_columnconfigure(0, weight=1)
        sfr.grid_columnconfigure(1, weight=0)
        sfr.grid(column=1, row=8, sticky=tk.NSEW)
        self._var_filename = tk.StringVar()
        self._var_filename.set(self.options['filename'])
        tk.Entry(sfr, textvariable=self._var_filename).grid(
            row=0, column=0, sticky=tk.NSEW)
        tk.Button(sfr, text="...", command=self._select_filename)\
            .grid(column=1, row=0)

        sfr = tk.Frame(self)
        sfr.grid(column=0, row=9, columnspan=2, sticky=tk.E)
        tk.Button(sfr, text="OK", command=self._ok)\
            .grid(column=0, row=0)
        tk.Button(sfr, text="Cancel", command=self.destroy)\
            .grid(column=1, row=0)

    def _ok(self):
        if not self.options['filename']:
            return

        self.options['tile_size'] = ((self._var_tile_w.get() or 256),
                                     (self._var_tile_h.get() or 256))
        self.options['create_tar'] = self._var_tar.get()
        self.options['force'] = self._var_force.get()
        self.options['format'] = self._var_format.get()
        jpeg_quality = self._var_jpg_quality.get()
        self.options['jpeg_quality'] = jpeg_quality if jpeg_quality > 0 \
            and jpeg_quality <= 100 else 80
        self.options['png_compression'] = self._var_png_comp.get()
        self.options['png_palette'] = self._var_png_palette.get()

        MapOptionsDialog._opts = self.options.copy()

        self.result = True
        self.destroy()

    def _select_filename(self):
        var_fname = self._var_filename.get()
        initialdir = os.path.dirname(var_fname) if var_fname else \
            self.last_dir
        fname = filedialog.asksaveasfilename(
            parent=self,
            filetypes=[("Map file", ".map"), ("All files", "*.*")],
            initialdir=initialdir,
            initialfile=var_fname)
        if fname:
            self.options['filename'] = fname
            self._var_filename.set(fname)
