#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright (c) Karol Będkowski, 2015-2020
# Distributed under terms of the GPLv3 license.

"""Mapmaker options dialog."""

import tkinter as tk
from tkinter import filedialog


class MapOptionsDialog(tk.Toplevel):
    """Dialog with options for new trekbuddy map."""

    def __init__(self, parent, last_dir, last_map_file, options=None):
        """Create dialog.

        :param parent: parent widget
        """
        tk.Toplevel.__init__(self, parent, borderwidth=5)
        self.transient(parent)
        self.options = {
            'tile_size': (256, 256),
            'create_tar': True,
            'force': False,
            'filename': "",
        }
        if options:
            self.options.update(options)

        self.last_dir = last_dir
        self.last_map_file = last_map_file
        self.result = False

        self.grid_columnconfigure(1, weight=1)

        tk.Label(self, text="Tile width").grid(row=0, column=0)
        self._var_tile_w = tk.IntVar()
        self._var_tile_w.set(self.options['tile_size'][0])
        tk.Entry(self, textvariable=self._var_tile_w).grid(row=0, column=1)

        tk.Label(self, text="Tile height").grid(row=1, column=0)
        self._var_tile_h = tk.IntVar()
        self._var_tile_h.set(self.options['tile_size'][1])
        tk.Entry(self, textvariable=self._var_tile_w).grid(row=1, column=1)

        self._var_tar = tk.BooleanVar()
        self._var_tar.set(self.options['force'])
        tk.Checkbutton(self, text="Create tar file", variable=self._var_tar)\
            .grid(row=3, columnspan=2, column=0, sticky=tk.NW)

        self._var_force = tk.BooleanVar()
        self._var_force.set(self.options['force'])
        tk.Checkbutton(self, text="Force create all tiles",
                       variable=self._var_force)\
            .grid(row=4, columnspan=2, column=0, sticky=tk.NW)

        tk.Label(self, text="Select map file name").grid(column=0, row=5)
        tk.Button(self, text="...", command=self._select_filename)\
            .grid(column=1, row=5)

        tk.Button(self, text="OK", command=self._ok)\
            .grid(column=0, row=6)
        tk.Button(self, text="Cancel", command=self.destroy)\
            .grid(column=1, row=6)

    def _ok(self):
        if not self.options['filename']:
            return

        self.options['tile_size'] = ((self._var_tile_w.get() or 256),
                                     (self._var_tile_h.get() or 256))
        self.options['create_tar'] = self._var_tar.get()
        self.options['force'] = self._var_force.get()

        self.result = True
        self.destroy()

    def _select_filename(self):
        fname = filedialog.asksaveasfilename(
            parent=self,
            filetypes=[("Map file", ".map"), ("All files", "*.*")],
            initialdir=self.last_dir,
            initialfile=self.last_map_file)
        if fname:
            self.options['filename'] = fname
