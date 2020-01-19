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
from tkinter import tix

from PIL import ImageTk

from . import mapfile
from .formatting import format_pos_latlon

__author__ = "Karol Będkowski"
__copyright__ = "Copyright (c) Karol Będkowski, 2015-2020"

_LOG = logging.getLogger(__name__)



class FormPosition:
    def __init__(self, parent):
        self.lat_m_v = tk.IntVar()
        self.lat_s_v = tk.DoubleVar()
        self.lat_d_v = tk.StringVar()
        self.lat_d_v.set('E')
        self.lon_m_v = tk.IntVar()
        self.lon_s_v = tk.DoubleVar()
        self.lon_d_v = tk.StringVar()
        self.lon_d_v.set('N')
        self.x = None
        self.y = None
        self.marker = None

    def reset(self):
        pass

    def __str__(self):
        return "<Position {}>".format(", ".join(
            "{}={:}".format(k, repr(v.get() if hasattr(v, 'get') else v))
            for k, v in self.__dict__.items()
            if k[0] != '_'
        ))

    def __repr__(self):
        return str(self)

    def set_lat(self, lat):
        self.lat_d_v.set('N')
        if lat < 0:
            lat *= 1
            self.lat_d_v.set('S')
        self.lat_m_v.set(int(lat))
        self.lat_s_v.set((lat - int(lat)) * 60.0)

    def set_lon(self, lon):
        self.lon_d_v.set('E')
        if lon < 0:
            lon *= 1
            self.lon_d_v.set('W')
        self.lon_m_v.set(int(lon))
        self.lon_s_v.set((lon - int(lon)) * 60.0)

    @property
    def lon(self):
        return (int(self.lon_m_v.get()) +
                float(self.lon_s_v.get()) / 60.0) * \
            (-1 if self.lon_d_v.get() == 'W' else 1)

    @property
    def lat(self):
        return (int(self.lat_m_v.get()) +
                float(self.lat_s_v.get()) / 60.0) * \
            (-1 if self.lat_d_v.get() == 'S' else 1)


class WndCalibrate(tk.Tk):
    def __init__(self, fname, mapfname=None):
        tk.Tk.__init__(self)

        style = ttk.Style()
        style.theme_use("clam")

        self._build_menu()
        self.title("TBViewer")

        self._last_dir = ""
        self._sel_point = tk.IntVar()
        self._sel_point.set(0)
        self._positions_data = [FormPosition(self) for _ in range(4)]
        self._click_pos = None
        self._img = None
        self._img_filename = None
        self._map_file = mapfile.MapFile()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        master = tk.Frame(self)
        master.grid(column=0, row=0, sticky=tk.NSEW)
        master.grid_rowconfigure(0, weight=1)
        master.grid_columnconfigure(0, weight=1)

        map_frame = self._create_map_frame(master)
        map_frame.grid(column=0, row=0, sticky=tk.NSEW)

        forms_frame = self._create_forms_frame(master)
        forms_frame.grid(column=1, row=0, sticky=tk.NSEW)

        self._status = tk.Label(master, text="", bd=1, relief=tk.SUNKEN,
                                anchor=tk.W)
        self._status.grid(column=0, row=1, columnspan=2, sticky=tk.EW)

        if fname:
            self._load(fname)

        if mapfname:
            self._load_map(mapfname)

        self._canvas.bind("<Configure>", self._draw)
        self._canvas.bind("<ButtonPress-1>", self._scroll_start)
        self._canvas.bind("<ButtonRelease-1>", self._scroll_end)
        self._canvas.bind("<Double-Button-1>", self._canvas_dclick)
        self._canvas.bind("<B1-Motion>", self._scroll_move)
        self._canvas.bind('<Motion>', self._canvas_mouse_motion)

        self.geometry("1024x768")

    def _create_map_frame(self, master):
        map_frame = tk.Frame(master, borderwidth=2, relief=tk.SUNKEN)
        map_frame.grid_columnconfigure(0, weight=1)
        map_frame.grid_rowconfigure(0, weight=1)

        h = ttk.Scrollbar(map_frame, orient=tk.HORIZONTAL)
        h.grid(column=0, row=1, sticky=tk.EW)
        h['command'] = self._move_scroll_h

        v = ttk.Scrollbar(map_frame, orient=tk.VERTICAL)
        v.grid(column=1, row=0, sticky=tk.NS)
        v['command'] = self._move_scroll_v

        self._canvas = tk.Canvas(map_frame, scrollregion=(0, 0, 1000, 1000),
                                 yscrollcommand=v.set, xscrollcommand=h.set)
        self._canvas.grid(column=0, row=0, sticky=tk.NSEW)
        return map_frame

    def _create_forms_frame(self, master):
        forms_frame = tk.Frame(master, borderwidth=2)
        for idx in range(4):
            self._create_latlon_form(idx, forms_frame)

        btns_frame = tk.Frame(forms_frame)
        btns_frame.grid()

        tk.Button(btns_frame, text="Calculate", command=self._calibrate)\
            .grid(column=0, row=0)

        tk.Button(btns_frame, text="Save Map...",
                  command=self._save_map_file)\
            .grid(column=1, row=0)

        return forms_frame

    def _create_latlon_form(self, idx, forms_frame):
        pos = self._positions_data[idx]
        form_frame = tk.Frame(forms_frame, borderwidth=5)
        form_frame.grid(column=0, row=idx, sticky=tk.NW)
        form_frame.grid_columnconfigure(0, weight=0)
        form_frame.grid_columnconfigure(1, weight=1)
        form_frame.grid_columnconfigure(2, weight=0)

        tk.Radiobutton(form_frame, text="Point " + str(idx+1),
                        variable=self._sel_point, value=idx)\
            .grid(row=0, columnspan=3)

        tk.Label(form_frame, text="Lon").grid(row=1, columnspan=3)
        tk.Entry(form_frame, textvariable=pos.lon_m_v, width=3).\
            grid(row=2, column=0)
        tk.Entry(form_frame, textvariable=pos.lon_s_v, width=12).\
            grid(row=2, column=1)
        tk.OptionMenu(form_frame, pos.lon_d_v, "E", "W").\
            grid(row=2, column=2)

        tk.Label(form_frame, text="Lat").grid(row=3, columnspan=3)
        tk.Entry(form_frame, textvariable=pos.lat_m_v, width=3).\
            grid(row=4, column=0)
        tk.Entry(form_frame, textvariable=pos.lat_s_v, width=12).\
            grid(row=4, column=1)
        tk.OptionMenu(form_frame, pos.lat_d_v, "N", "S").\
            grid(row=4, column=2)
        ttk.Separator(form_frame, orient=tk.HORIZONTAL)\
            .grid(row=5, columnspan=4, sticky=tk.EW, pady=5)

    def onExit(self):
        self.quit()

    def _build_menu(self):
        menubar = tk.Menu(self)
        self.config(menu=menubar)
        file_menu = tk.Menu(menubar, tearoff=False)
        file_menu.add_command(label="Open image...", command=self._open_file)
        file_menu.add_command(label="Open map file...",
                              command=self._open_map_file)
        file_menu.add_command(label="Save map file...",
                              command=self._save_map_file)
        file_menu.add_command(label="Calibrate", command=self._calibrate)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.onExit)
        menubar.add_cascade(label="File", menu=file_menu)

    def _open_file(self):
        fname = filedialog.askopenfilename(
            parent=self,
            filetypes=[("Supported files", ".jpg .jpeg .png"),
                       ("All files", "*.*")],
            initialdir=self._last_dir)
        if fname:
            self._load(fname)
            self._last_dir = os.path.dirname(fname)
            for p in self._positions_data:
                p.reset()

    def _load(self, fname):
        self._canvas.delete('img')
        self._img = img = ImageTk.PhotoImage(file=fname)
        self._canvas.create_image(20, 20, image=img, anchor=tk.NW)
        self._canvas.config(
            width=img.width() + 40,
            height=img.height() + 40,
            scrollregion=(0, 0, img.width() + 40, img.height() + 40))
        self.update_idletasks()

    def _open_map_file(self):
        fname = filedialog.askopenfilename(
            parent=self,
            filetypes=[("Map file", ".map"),
                       ("All files", "*.*")],
            initialdir=self._last_dir)
        if fname:
            self._load_map(fname)
            self._last_dir = os.path.dirname(fname)

    def _load_map(self, fname):
        with open(fname) as f:
            content = f.read()
        self._map_file.parse_map(content)
        self._map_file.filename = fname
        _LOG.debug(self._map_file.to_str())
        for idx, p in enumerate(self._map_file.points[:4]):
            pdata = self._positions_data[idx]
            pdata.set_lat(p.lat)
            pdata.set_lon(p.lon)
            pdata.x = p.x
            pdata.y = p.y
        self._draw()

    def _save_map_file(self):
        if not self._map_file.validate():
            _LOG.warn("map not valid")
            return
        fname = filedialog.asksaveasfilename(
            parent=self,
            filetypes=[("Map file", ".map"),
                       ("All files", "*.*")],
            initialdir=self._last_dir,
            initialfile=self._map_file.filename)
        if fname:
            self._map_file.img_filename = self._img_filename
            self._map_file.img_filepath = os.path.dirname(self._img_filename)
            content = self._map_file.to_str()
            with open(fname, 'w') as f:
                f.write(content)
            self._map_file.filename = fname

    def _move_scroll_v(self, scroll, num, units=None):
        self._canvas.yview(scroll, num, units)
        self._draw()

    def _move_scroll_h(self, scroll, num, units=None):
        self._canvas.xview(scroll, num, units)
        self._draw()

    def _scroll_start(self, event):
        self._click_pos = (event.x, event.y)
        self._canvas.scan_mark(event.x, event.y)
        self._draw()

    def _scroll_end(self, event):
        if (event.x, event.y) != self._click_pos:
            return
        _LOG.info("click")

    def _scroll_move(self, event):
        self._canvas.scan_dragto(event.x, event.y, gain=1)
        self._draw()

    def _canvas_dclick(self, event):
        x = self._canvas.canvasx(event.x)
        y = self._canvas.canvasy(event.y)
        selected = self._sel_point.get()
        _LOG.info("dclick %s %s %s", x, y, selected)
        self._positions_data[selected].x = x - 20
        self._positions_data[selected].y = y - 20
        self._draw()

    def _canvas_mouse_motion(self, event):
        if not self._img:
            return

        x = self._canvas.canvasx(event.x) - 20
        y = self._canvas.canvasy(event.y) - 20
        pos = self._map_file.xy2latlon(x, y)
        info = format_pos_latlon(pos[0], pos[1]) if pos else ""
        self._status.config(text="x={}  y={};       {}".format(x, y, info))

    def _draw(self, clear=False):
        canvas = self._canvas
        for idx, point in enumerate(self._positions_data):
            x, y = point.x, point.y
            if x is not None and y is not None:
                x += 20
                y += 20

                p = self._positions_data[idx].marker
                if p:
                    canvas.coords(p[0], x, y - 20, x, y + 20)
                    canvas.coords(p[1], x - 20, y, x + 20, y)
                    canvas.coords(p[2], x + 7, y + 7)  # label
                    canvas.coords(p[3], x - 20, y - 20, x + 20, y + 20)
                    canvas.coords(p[4], x - 20, y - 20, x + 20, y + 20)
                else:
                    l1 = canvas.create_line(x, y - 20, x, y + 20, fill="red")
                    l2 = canvas.create_line(x - 20, y, x + 20, y, fill="red")
                    o = canvas.create_oval(x - 20, y - 20, x + 20, y + 20,
                                           activewidth="6", width="5",
                                           outline="black")
                    o2 = canvas.create_oval(x - 20, y - 20, x + 20, y + 20,
                                            activewidth="3", width="2",
                                            outline="red")
                    t = canvas.create_text(x + 7, y + 7, fill="red",
                                           text=str(idx + 1))
                    self._positions_data[idx].marker = (l1, l2, t, o, o2)

        self.update_idletasks()

    def _calibrate(self):
        for i in self._positions_data:
            _LOG.info(repr(i))

        if not all(p.x is not None and p.y is not None
                   for p in self._positions_data):
            return

        if not self._img:
            return

        self._map_file.image_width = self._img.width()
        self._map_file.image_height = self._img.height()
        points = [mapfile.Point(p.x, p.y, p.lon, p.lat)
                  for p in self._positions_data]
        self._map_file.set_points(points)
        self._map_file.calibrate()
        _LOG.debug(str(self._map_file.to_str()))

    def _test_calc(self):
        pos = [
            (204, 506, 18.0 + 48/60., 49.0 + 48/60.),
            (5116, 506, 19.0 + 14/60., 49.0 + 48/60.),
            (5138, 7507, 19.0 + 14/60., 49.0 + 24/60.),
            (1710, 7509, 18.0 + 56/60., 49.0 + 24/60.),
        ]
        for i, p in enumerate(pos):
            pd = self._positions_data[i]
            pd.x, pd.y = p[0], p[1]
            pd.set_lat(p[2])
            pd.set_lon(p[3])
        self._calibrate()
