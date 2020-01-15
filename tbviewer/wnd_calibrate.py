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

__author__ = "Karol Będkowski"
__copyright__ = "Copyright (c) Karol Będkowski, 2015-2020"

_LOG = logging.getLogger(__name__)


class FakePosition:
    def __init__(self, x, y, lat, lon):
        self.lat_m = float(int(lat))
        self.lat_s = (lat - self.lat_m) * 60.0
        self.lat_d = 'E'
        self.lon_m = float(int(lon))
        self.lon_s = (lon - self.lon_m) * 60.0
        self.lon_d = 'N'
        self.x = x
        self.y = y

    def __str__(self):
        return "<FakePosition {}>".format(", ".join(
            "{}={:}".format(k, repr(v))
            for k, v in self.__dict__.items()
            if k[0] != '_'
        ))

    def __repr__(self):
        return str(self)

    @property
    def lon(self):
        return (self.lon_m + self.lon_s / 60.0) * \
            (-1 if self.lon_d == 'S' else 1)

    @property
    def lat(self):
        return (self.lat_m + self.lat_s / 60.0) * \
            (-1 if self.lat_d == 'W' else 1)


class Position:
    def __init__(self, parent):
        self.lat_m_v = tk.StringVar()
        self.lat_s_v = tk.StringVar()
        self.lat_d_v = tk.StringVar()
        self.lat_d_v.set('E')
        self.lon_m_v = tk.StringVar()
        self.lon_s_v = tk.StringVar()
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

    @property
    def lat_m(self):
        return float(self.lat_m_v.get() or '0')

    @property
    def lat_s(self):
        return float(self.lat_s_v.get() or '0')

    @property
    def lat_d(self):
        return self.lat_d_v.get()

    @property
    def lon_m(self):
        return float(self.lon_m_v.get() or '0')

    @property
    def lon_s(self):
        return float(self.lon_s_v.get() or '0')

    @property
    def lon_d(self):
        return self.lon_d_v.get()


    @property
    def lon(self):
        return (self.lon_m + self.lon_s / 60.0) * \
            (-1 if self.lon_d == 'S' else 1)

    @property
    def lat(self):
        return (self.lat_m + self.lat_s / 60.0) * \
            (-1 if self.lat_d == 'W' else 1)


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
        self._positions_data = [Position(self) for _ in range(4)]
        self._click_pos = None
        self._cal_points = None

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
        file_menu.add_command(label="Open", command=self._open_file)
        file_menu.add_command(label="Calibrate", command=self._calibrate)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.onExit)
        menubar.add_cascade(label="File", menu=file_menu)

    def _open_file(self):
        fname = filedialog.askopenfilename(parent=self,
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
        x = self._canvas.canvasx(event.x)
        y = self._canvas.canvasy(event.y)
        info = ""
        if self._cal_points:
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

        map_file = MapFile()
        map_file.set_image_size(self._img.width(), self._img.height())
        map_file.calculate(self._positions_data)
        _LOG.debug(str(map_file.format_str()))
        self._cal_points = map_file.corners
        _LOG.debug(repr(self._cal_points))

    def xy2lonlat(self, x, y):
        """ Calculate lon & lat from position. """
        return _map_xy_lonlat(
            self._cal_points[0][2:], self._cal_points[1][2:],
            self._cal_points[2][2:], self._cal_points[3][2:],
            self._img.width(), self._img.height(),
            x, y)

    def _test_calc(self):
        pos = [
            FakePosition(224, 526, 18.0 + 48/60., 49.0 + 48/60.),
            FakePosition(5136, 526, 19.0 + 14/60., 49.0 + 48/60.),
            FakePosition(5158, 7527, 19.0 + 14/60., 49.0 + 24/60.),
            FakePosition(1730, 7529, 18.0 + 56/60., 49.0 + 24/60.),
        ]

        self._cal_points = calculate(pos, 5357, 7685)
        _LOG.debug(repr(self._cal_points))


_MAP_POINT_TEMPLATE = \
    "Point{idx},xy,{x:>5},{y:>5},in, deg,{lat_m:>4},{lat_s:>8},{lat_d},"\
    "{lon_m:>4},{lon_s:>8},{lon_d}, grid,   ,           ,           ,N"

_MAP_MMPXY_TEMPLATE = "MMPXY,{idx},{x},{y}"
_MAP_MMPLL_TEMPLATE = "MMPLL,{idx},{lat:>11},{lon:>11}"

_MAP_TEMPALTE = """OziExplorer Map Data File Version 2.2
{filename}
{filepath}
1 ,Map Code,
WGS 84,WGS 84,   0.0000,   0.0000,WGS 84
Reserved 1
Reserved 2
Magnetic Variation,,,E
Map Projection,Latitude/Longitude,PolyCal,No,AutoCalOnly,No,BSBUseWPX,No
{points}
Projection Setup,,,,,,,,,,
Map Feature = MF ; Map Comment = MC     These follow if they exist
Track File = TF      These follow if they exist
Moving Map Parameters = MM?    These follow if they exist
MM0,Yes
MMPNUM,{mmplen}
{mmpxy}
{mmpll}
MM1B,4.450529
MOP,Map Open Position,0,0
IWH,Map Image Width/Height,{image_width},{image_height}
"""


class MapFile:
    def __init__(self):
        self.image_width = 0
        self.image_height = 0
        self.markers = []
        self.corners = []

    def __str__(self):
        return "<MapFile: points={}, image_width={}, image_height={}".format(
            self.markers, self.image_width, self.image_height
        )

    def set_image_size(self, width, height):
        self.image_width = width
        self.image_height = height

    def calculate(self, points):
        self.markers= points
        self.corners = calculate(self.markers, self.image_width,
                                 self.image_height)
        _LOG.debug("corners: %r", self.corners)

    def format_str(self):
        points = [_MAP_POINT_TEMPLATE.format(
            idx=idx, x=int(p.x), y=int(p.y),
            lat_m=int(p.lat_m), lat_s=p.lat_s, lat_d=p.lat_d,
            lon_m=int(p.lon_m), lon_s=p.lon_s, lon_d=p.lon_d)
            for idx, p in enumerate(self.markers)
        ]
        mmpxy = [_MAP_MMPXY_TEMPLATE.format(idx=idx+1, x=x, y=y)
                 for idx, (x, y, _, _) in enumerate(self.corners)]
        mmpll = [_MAP_MMPLL_TEMPLATE.format(idx=idx+1, lat=lat, lon=lon)
                 for idx, (_, _, lat, lon) in enumerate(self.corners)]
        return _MAP_TEMPALTE.format(
            filename="dummy.jpg",
            filepath="dummy.jpg",
            points="\n".join(points),
            mmplen=0,
            mmpxy="\n".join(mmpxy),
            mmpll="\n".join(mmpll),
            image_width=self.image_width, image_height=self.image_height
        )



def sort_points(positions, width, height):
    def dist_from(pos, x0, y0):
        return math.sqrt((pos.x - x0) ** 2 + (pos.y - y0) ** 2)

    positions = sorted(positions, key=lambda x: dist_from(x, 0, 0))
    nw, positions = positions[0], positions[1:]
    positions = sorted(positions, key=lambda x: dist_from(x, width, 0))
    ne, positions = positions[0], positions[1:]
    positions = sorted(positions, key=lambda x: dist_from(x, 0, height))
    sw, se = positions
    _LOG.debug(repr(locals()))
    return (nw, ne, se, sw)


def prettydict(d):
    return "\n".join(
        str(key) + "=" + repr(val)
        for key, val in sorted(d.items())
    )

def calculate(positions, width, height):
    poss = sort_points(positions, width, height)
    p0, p1, p2, p3 = poss

    # west/east
    dlat = p0.lat - p2.lat
    dx = p0.x - p2.x
    w_lat = p0.lat - (dlat / dx) * p0.x
    e_lat = w_lat + (dlat / dx) * width

    # north / south
    dlon = p0.lon - p2.lon
    dy = p0.y - p2.y
    n_lon = p0.lon - (dlon / dy) * p0.y
    s_lon = n_lon + (dlon / dy) * height
    _LOG.debug(prettydict(locals()))

    return [
        (0, 0, w_lat, n_lon),
        (width, 0, e_lat, n_lon),
        (width, height, e_lat, s_lon),
        (0, height, w_lat, s_lon)
    ]


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
