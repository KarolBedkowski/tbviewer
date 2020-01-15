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
        self.lat_d_v.set('E')
        if lat < 0:
            lat *= 1
            self.lat_d_v.set('W')
        self.lat_m_v.set(int(lat))
        self.lat_s_v.set((lat - int(lat)) * 60.0)

    def set_lon(self, lon):
        self.lon_d_v.set('N')
        if lon < 0:
            lon *= 1
            self.lon_d_v.set('S')
        self.lon_m_v.set(int(lon))
        self.lon_s_v.set((lon - int(lon)) * 60.0)

    @property
    def lon(self):
        return (int(self.lon_m_v.get()) +
                float(self.lon_s_v.get()) / 60.0) * \
            (-1 if self.lon_d_v.get() == 'S' else 1)

    @property
    def lat(self):
        return (int(self.lat_m_v.get()) +
                float(self.lat_s_v.get()) / 60.0) * \
            (-1 if self.lat_d_v.get() == 'W' else 1)


class WndCalibrate(tk.Tk):
    def __init__(self, fname):
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
        self._map_file = mapfile.MapFile()

        master = tk.Frame(self)
        master.grid(column=0, row=0, sticky=tk.NSEW)
        master.grid_rowconfigure(0, weight=1)
        master.grid_columnconfigure(0, weight=0)
        master.grid_columnconfigure(1, weight=1)

        left_frame = tk.Frame(master, borderwidth=2, relief=tk.SUNKEN)
        left_frame.grid(column=0, row=0, sticky=tk.NSEW)

        for idx in range(4):
            pos = self._positions_data[idx]
            form_frame = tk.Frame(left_frame)
            form_frame.grid(column=0, row=idx, sticky=tk.NW)

            tk.Radiobutton(form_frame, text="Point " + str(idx+1),
                           variable=self._sel_point, value=idx)\
                .grid(row=0, columnspan=3)

            tk.Label(form_frame, text="Lon").grid(row=1, columnspan=3)
            tk.Entry(form_frame, textvariable=pos.lon_m_v).grid(row=2, column=0)
            tk.Entry(form_frame, textvariable=pos.lon_s_v).grid(row=2, column=1)
            tk.OptionMenu(form_frame, pos.lon_d_v, "N", "S").\
                grid(row=2, column=2)

            tk.Label(form_frame, text="Lat").grid(row=3, columnspan=3)
            tk.Entry(form_frame, textvariable=pos.lat_m_v).grid(row=4, column=0)
            tk.Entry(form_frame, textvariable=pos.lat_s_v).grid(row=4, column=1)
            tk.OptionMenu(form_frame, pos.lat_d_v, "E", "W").\
                grid(row=4, column=2)
            ttk.Separator(form_frame, orient=tk.HORIZONTAL)\
                .grid(row=5, columnspan=4, sticky=tk.EW, pady=5)

        tk.Button(form_frame, text="Calculate", command=self._test_calc)\
            .grid(columnspan=3)

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

        self._canvas.bind("<Configure>", self._draw_tiles)
        self._canvas.bind("<ButtonPress-1>", self._scroll_start)
        self._canvas.bind("<ButtonRelease-1>", self._scroll_end)
        self._canvas.bind("<Double-Button-1>", self._canvas_dclick)
        self._canvas.bind("<B1-Motion>", self._scroll_move)
        self._canvas.bind('<Motion>', self._canvas_mouse_motion)

        self.geometry("1024x768")

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
        _LOG.debug(self._map_file.to_str())
        for idx, p in enumerate(self._map_file.points[:4]):
            pdata = self._positions_data[idx]
            pdata.set_lat(p.lat)
            pdata.set_lon(p.lon)
            pdata.x = p.x
            pdata.y = p.y
        self._draw_tiles()

    def _save_map_file(self):
        if not self._map_file.validate():
            return
        fname = filedialog.asksaveasfilename(
            parent=self,
            filetypes=[("Map file", ".map"),
                       ("All files", "*.*")],
            initialdir=self._last_dir)
        if fname:
            content = self._map_file.to_str()
            with open(fname, 'w') as f:
                f.write(content)

    def _move_scroll_v(self, scroll, num, units=None):
        self._canvas.yview(scroll, num, units)
        self._draw_tiles()

    def _move_scroll_h(self, scroll, num, units=None):
        self._canvas.xview(scroll, num, units)
        self._draw_tiles()

    def _scroll_start(self, event):
        self._click_pos = (event.x, event.y)
        self._canvas.scan_mark(event.x, event.y)
        self._draw_tiles()

    def _scroll_end(self, event):
        if (event.x, event.y) != self._click_pos:
            return
        _LOG.info("click")

    def _scroll_move(self, event):
        self._canvas.scan_dragto(event.x, event.y, gain=1)
        self._draw_tiles()

    def _canvas_dclick(self, event):
        x = self._canvas.canvasx(event.x)
        y = self._canvas.canvasy(event.y)
        selected = self._sel_point.get()
        _LOG.info("dclick %s %s %s", x, y, selected)
        self._positions_data[selected].x = x
        self._positions_data[selected].y = y
        self._draw_tiles()

    def _canvas_mouse_motion(self, event):
        if not self._img:
            return

        x = self._canvas.canvasx(event.x)
        y = self._canvas.canvasy(event.y)
        info = ""
        if self._map_file.mmpll:
            pos = self.xy2lonlat(x, y)
            info = _format_degree(pos[0]) + " " + _format_degree(pos[1], False)
        self._status.config(text="x={}  y={}; {}".format(x, y, info))

    def _draw_tiles(self, clear=False):
        tstart = time.time()
        canvas = self._canvas

        for idx, point in enumerate(self._positions_data):
            x, y = point.x, point.y
            if x is not None and y is not None:
                p = self._positions_data[idx].marker
                if p:
                    canvas.coords(p[0], x, y - 20, x, y + 20)
                    canvas.coords(p[1], x - 20, y, x + 20, y)
                    canvas.coords(p[2], x + 10, y + 10)
                    canvas.coords(p[3], x - 20, y - 20, x + 20, y + 20)
                    canvas.coords(p[4], x - 20, y - 20, x + 20, y + 20)
                else:
                    l1 = canvas.create_line(x, y - 20, x, y + 20, fill="red")
                    l2 = canvas.create_line(x - 20, y, x + 20, y, fill="red")
                    t = canvas.create_text(x + 10, y + 10, fill="red",
                                           text=str(idx + 1))
                    o = canvas.create_oval(x - 20, y - 20, x + 20, y + 20,
                                           activewidth="6", width="5",
                                           outline="black")
                    o2 = canvas.create_oval(x - 20, y - 20, x + 20, y + 20,
                                            activewidth="3", width="2",
                                            outline="red")
                    self._positions_data[idx].marker = (l1, l2, t, o, o2)

        self.update_idletasks()
        _LOG.debug("_draw_tiles in %s", time.time() - tstart)

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
        points = [(p.x, p.y, p.lat, p.lon) for p in self._positions_data]
        self._map_file.set_points(points)
        self._map_file.calibrate()
        _LOG.debug(str(self._map_file.to_str()))

    def xy2lonlat(self, x, y):
        """ Calculate lon & lat from position. """
        cal_points = self._map_file.mmpll
        return _map_xy_lonlat(
            cal_points[0], cal_points[1],
            cal_points[2], cal_points[3],
            self._img.width(), self._img.height(),
            x, y)

    def _test_calc(self):
        pos = [
            (224, 526, 18.0 + 48/60., 49.0 + 48/60.),
            (5136, 526, 19.0 + 14/60., 49.0 + 48/60.),
            (5158, 7527, 19.0 + 14/60., 49.0 + 24/60.),
            (1730, 7529, 18.0 + 56/60., 49.0 + 24/60.),
        ]
        for i, p in enumerate(pos):
            pd = self._positions_data[i]
            pd.x, pd.y = p[0], p[1]
            pd.set_lat(p[2])
            pd.set_lon(p[3])
        self._calibrate()



def prettydict(d):
    return "\n".join(
        str(key) + "=" + repr(val)
        for key, val in sorted(d.items())
    )


def _format_degree(degree, latitude=True, short=True):
    lit = ["NS", "EW"][0 if latitude else 1][0 if degree > 0 else 1]
    degree = abs(degree)
    mint, stop = math.modf(degree)
    if short:
        return "%d %s' %s" % (stop,
                              locale.format('%0.2f', mint * 60), lit)
    sec, mint = math.modf(mint * 60)
    return "%d %d' %s'' %s" % (stop, mint,
                               locale.format('%0.2f', sec * 60), lit)

def _map_xy_lonlat(xy0, xy1, xy2, xy3, sx, sy, x, y):
    x0, y0 = xy0
    x1, y1 = xy1
    x2, y2 = xy2
    x3, y3 = xy3

    syy = sy - y
    sxx = sx - x

    return _intersect_lines(
        (syy * x0 + y * x3) / sy, (syy * y0 + y * y3) / sy,
        (syy * x1 + y * x2) / sy, (syy * y1 + y * y2) / sy,
        (sxx * x0 + x * x1) / sx, (sxx * y0 + x * y1) / sx,
        (sxx * x3 + x * x2) / sx, (sxx * y3 + x * y2) / sx)


def _det(a, b, c, d):
    return a * d - b * c


def _intersect_lines(x1, y1, x2, y2, x3, y3, x4, y4):
    d = _det(x1 - x2, y1 - y2, x3 - x4, y3 - y4) or 1
    d1 = _det(x1, y1, x2, y2)
    d2 = _det(x3, y3, x4, y4)
    px = _det(d1, x1 - x2, d2, x3 - x4) / d
    py = _det(d1, y1 - y2, d2, y3 - y4) / d
    return px, py
