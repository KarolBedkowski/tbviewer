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

        tk.Label(self, text="Tile width").grid(row=0, column=0)
        self._var_tile_w = tk.IntVar()
        self._var_tile_w.set(self.options['tile_size'][0])
        tk.Entry(self, textvariable=self._var_tile_w).grid(
            row=0, column=1, sticky=tk.NW)

        tk.Label(self, text="Tile height").grid(row=1, column=0)
        self._var_tile_h = tk.IntVar()
        self._var_tile_h.set(self.options['tile_size'][1])
        tk.Entry(self, textvariable=self._var_tile_w).grid(
            row=1, column=1, sticky=tk.NW)

        self._var_tar = tk.BooleanVar()
        self._var_tar.set(self.options['force'])
        tk.Checkbutton(self, text="Create tar file", variable=self._var_tar)\
            .grid(row=3, columnspan=2, column=0, sticky=tk.NW)

        self._var_force = tk.BooleanVar()
        self._var_force.set(self.options['force'])
        tk.Checkbutton(self, text="Force create all tiles",
                       variable=self._var_force)\
            .grid(row=4, columnspan=2, column=0, sticky=tk.NW)

        tk.Label(self, text="Map file name").grid(column=0, row=5)
        sfr = tk.Frame(self, pady=10)
        sfr.grid_columnconfigure(0, weight=1)
        sfr.grid_columnconfigure(1, weight=0)
        sfr.grid(column=1, row=5, sticky=tk.NSEW)
        self._var_filename = tk.StringVar()
        self._var_filename.set(self.options['filename'])
        tk.Entry(sfr, textvariable=self._var_filename).grid(
            row=0, column=0, sticky=tk.NSEW)
        tk.Button(sfr, text="...", command=self._select_filename)\
            .grid(column=1, row=0)

        sfr = tk.Frame(self)
        sfr.grid(column=0, row=6, columnspan=2, sticky=tk.E)
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
