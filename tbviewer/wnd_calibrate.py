#!/usr/bin/python3
# vim:fenc=utf-8
# Copyright (c) Karol Będkowski, 2015-2020
#
# This file is part of tbviewer
# Distributed under terms of the GPLv3 license.

"""Main window for calibration module."""

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

from PIL import ImageTk, Image

from . import mapfile
from . import formatting
from . import dialogs
from . import tkutils
from . import mapmaker
from . import wnd_mapoptions
from .errors import InvalidFileException

_LOG = logging.getLogger(__name__)


def _check_variable_val(variable, min_value, max_value):
    try:
        value = variable.get()
        return value >= min_value and value <= max_value
    except:
        return False


class FormPosition:
    def __init__(self, parent):
        self.lat_m = tk.IntVar()
        self.lat_s = tk.DoubleVar()
        self.lat_d = tk.StringVar()
        self.lat_d.set('E')
        self.lon_m = tk.IntVar()
        self.lon_s = tk.DoubleVar()
        self.lon_d = tk.StringVar()
        self.lon_d.set('N')
        self.x = None
        self.y = None
        self.marker = None

    def reset(self):
        self.x = None
        self.y = None
        self.set_lon(0)
        self.set_lat(0)
        self.marker = None

    def __str__(self):
        return "<Position {}>".format(", ".join(
            "{}={:}".format(k, repr(v.get() if hasattr(v, 'get') else v))
            for k, v in self.__dict__.items()
            if k[0] != '_'
        ))

    def __repr__(self):
        return str(self)

    def set_lat(self, lat):
        self.lat_d.set('N')
        if lat < 0:
            lat *= 1
            self.lat_d.set('S')
        s, m = math.modf(lat)
        self.lat_m.set(int(m))
        self.lat_s.set(s * 60.0)

    def set_lon(self, lon):
        self.lon_d.set('E')
        if lon < 0:
            lon *= 1
            self.lon_d.set('W')
        s, m = math.modf(lon)
        self.lon_m.set(int(m))
        self.lon_s.set(s * 60.0)

    @property
    def lon(self):
        return (int(self.lon_m.get()) +
                float(self.lon_s.get()) / 60.0) * \
            (-1 if self.lon_d.get() == 'W' else 1)

    @property
    def lat(self):
        return (int(self.lat_m.get()) +
                float(self.lat_s.get()) / 60.0) * \
            (-1 if self.lat_d.get() == 'S' else 1)

    def validate_lon_m(self):
        return _check_variable_val(self.lon_m, -180, 180)

    def validate_lon_s(self):
        return _check_variable_val(self.lon_s, 0.0, 60.0)

    def validate_lat_m(self):
        return _check_variable_val(self.lat_m, -90, 90)

    def validate_lat_s(self):
        return _check_variable_val(self.lat_s, 0.0, 60.0)

    def validate(self):
        return self.x is not None and self.y is not None \
            and self.validate_lon_m() and self.validate_lon_s \
            and self.validate_lat_m() and self.validate_lat_s


class WndCalibrate(tk.Tk):
    def __init__(self, fname, mapfname=None):
        tk.Tk.__init__(self)

        style = ttk.Style()
        style.theme_use("clam")

        self._build_menu()
        self.title("TBViewer")

        self._busy_manager = tkutils.BusyManager(self)
        self._last_dir = ""
        self._sel_point = tk.IntVar()
        self._sel_point.set(0)
        self._positions_data = [FormPosition(self) for _ in range(4)]
        self._click_pos = None
        self._img = None
        self._img_filename = None
        self._map_file = mapfile.MapFile()
        self._scale = 0

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

        self._create_status_frame(master).\
            grid(column=0, row=1, columnspan=2, sticky=tk.EW)

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
        # with Windows OS
        self._canvas.bind("<MouseWheel>", self._canvas_mouse_wheel)
        # with Linux OS
        self._canvas.bind("<Button-4>", self._canvas_mouse_wheel)
        self._canvas.bind("<Button-5>", self._canvas_mouse_wheel)

        self.geometry("1024x768")

    def _create_status_frame(self, master):
        status_frame = tk.Frame(master)
        self._status_x = tk.Label(status_frame, text="", bd=1,
                                  relief=tk.SUNKEN, anchor=tk.W)
        self._status_x.grid(column=0, row=0, ipadx=3)
        self._status_y = tk.Label(status_frame, text="", bd=1,
                                  relief=tk.SUNKEN, anchor=tk.W)
        self._status_y.grid(column=1, row=0, ipadx=3)
        self._status_lat = tk.Label(status_frame, text="", bd=1,
                                    relief=tk.SUNKEN, anchor=tk.W)
        self._status_lat.grid(column=2, row=0, ipadx=3)
        self._status_lon = tk.Label(status_frame, text="", bd=1,
                                    relief=tk.SUNKEN, anchor=tk.W)
        self._status_lon.grid(column=3, row=0, ipadx=3)
        self._status_zoom = tk.Label(status_frame, text="", bd=1,
                                     relief=tk.SUNKEN, anchor=tk.W)
        self._status_zoom.grid(column=4, row=0, ipadx=3)
        return status_frame

    def _create_map_frame(self, master):
        map_frame = tk.Frame(master, borderwidth=2, relief=tk.SUNKEN)
        map_frame.grid_columnconfigure(0, weight=1)
        map_frame.grid_rowconfigure(0, weight=1)

        h = ttk.Scrollbar(map_frame, orient=tk.HORIZONTAL,
                          command=self._move_scroll_h)
        h.grid(column=0, row=1, sticky=tk.EW)

        v = ttk.Scrollbar(map_frame, orient=tk.VERTICAL,
                          command=self._move_scroll_v)
        v.grid(column=1, row=0, sticky=tk.NS)

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
            .grid(column=0, row=0, columnspan=2)

        tk.Button(btns_frame, text="Save Map...", command=self._save_map_file)\
            .grid(column=0, row=1)

        tk.Button(btns_frame, text="Save TBMap...",
                  command=self._save_cut_map)\
            .grid(column=1, row=1)

        return forms_frame

    def _create_latlon_form(self, idx, forms_frame):
        pos = self._positions_data[idx]
        form_frame = tk.Frame(forms_frame, borderwidth=5)
        form_frame.grid(column=0, row=idx, sticky=tk.NW)
        form_frame.grid_columnconfigure(0, weight=0)
        form_frame.grid_columnconfigure(1, weight=1)
        form_frame.grid_columnconfigure(2, weight=0)

        tk.Radiobutton(form_frame, text="Point " + str(idx+1),
                       variable=self._sel_point, value=idx,
                       command=self._on_point_rb)\
            .grid(row=0, columnspan=3)

        tk.Label(form_frame, text="Lon").grid(row=1, columnspan=3)
        tk.Entry(form_frame, textvariable=pos.lon_m, width=4,
                 validate="focus", validatecommand=pos.validate_lon_m).\
            grid(row=2, column=0)
        tk.Entry(form_frame, textvariable=pos.lon_s, width=12,
                 validate="focus", validatecommand=pos.validate_lon_s).\
            grid(row=2, column=1)
        tk.OptionMenu(form_frame, pos.lon_d, "E", "W").\
            grid(row=2, column=2)

        tk.Label(form_frame, text="Lat").grid(row=3, columnspan=3)
        tk.Entry(form_frame, textvariable=pos.lat_m, width=3,
                 validate="focus", validatecommand=pos.validate_lat_m).\
            grid(row=4, column=0)
        tk.Entry(form_frame, textvariable=pos.lat_s, width=12,
                 validate="focus", validatecommand=pos.validate_lat_s).\
            grid(row=4, column=1)
        tk.OptionMenu(form_frame, pos.lat_d, "N", "S").\
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
        file_menu.add_command(label="Save TBmap...",
                              command=self._save_cut_map)
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

    def _load_img(self, fname):
        if self._scale == 0:
            return ImageTk.PhotoImage(file=fname)

        img = Image.open(fname)
        scale = 2 ** self._scale
        img = img.resize((int(img.width * scale), int(img.height * scale)),
                         Image.ANTIALIAS)
        img = ImageTk.PhotoImage(img)
        return img

    def _load(self, fname):
        if not fname:
            return
        self._busy_manager.busy()
        self.update()
        self._canvas.delete('img')
        self._img = None
        try:
            self._img = img = self._load_img(fname)
        except IOError as err:
            messagebox.showerror(
                "Error loading file", f"Invalid file: {err}")
        else:
            self._canvas.create_image(20, 20, image=img, anchor=tk.NW)
            self._canvas.config(
                width=img.width() + 40,
                height=img.height() + 40,
                scrollregion=(0, 0, img.width() + 40, img.height() + 40))
            self.update_idletasks()
            self._img_filename = fname
            if self._map_file.image_width != img.width() or \
                    self._map_file.image_height != img.height():
                self._map_file.clear()
                for p in self._positions_data:
                    p.reset()
            self._canvas.delete('marker')

        self._busy_manager.notbusy()

    def _open_map_file(self):
        if not self._img:
            messagebox.showerror(
                "Error loading file", "Please open image file first.")
            return

        fname = filedialog.askopenfilename(
            parent=self,
            filetypes=[("Map file", ".map"), ("All files", "*.*")],
            initialdir=self._last_dir)
        if fname:
            try:
                self._load_map(fname)
            except InvalidFileException as err:
                messagebox.showerror(
                    "Error loading file", f"Invalid file: {err}")
            else:
                self._last_dir = os.path.dirname(fname)

    def _load_map(self, fname):
        self._busy_manager.busy()
        self.update()
        with open(fname) as f:
            content = f.read()
        self._map_file.parse_map(content)
        self._map_file.filename = fname
        for idx, p in enumerate(self._map_file.points[:4]):
            pdata = self._positions_data[idx]
            pdata.set_lat(p.lat)
            pdata.set_lon(p.lon)
            pdata.x = p.x
            pdata.y = p.y
        self._busy_manager.notbusy()
        self._draw()

    def _save_map_file(self):
        if not self._validate():
            return

        fname = filedialog.asksaveasfilename(
            parent=self,
            filetypes=[("Map file", ".map"), ("All files", "*.*")],
            initialdir=self._last_dir,
            initialfile=self._map_file.filename)
        if fname:
            content = self._map_file.to_str()
            try:
                with open(fname, 'w') as f:
                    f.write(content)
            except IOError as err:
                messagebox.showerror("Save file error", str(err))
            else:
                self._map_file.filename = fname

    def _save_cut_map(self):
        if not self._validate():
            return

        dlg = wnd_mapoptions.MapOptionsDialog(
            self, self._last_dir, self._map_file.filename)
        self.wait_window(dlg)
        if not dlg.result:
            return
        content = self._map_file.to_str()
        try:
            mapmaker.create_map(
                self._img_filename,
                content,
                dlg.options['filename'],
                options=dlg.options
            )
        except IOError as err:
            messagebox.showerror("Save file error", str(err))
        else:
            messagebox.showinfo("Create map", "Trekbuddy map file created")

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

    def _scroll_move(self, event):
        self._canvas.scan_dragto(event.x, event.y, gain=1)
        self._draw()

    def _canvas_dclick(self, event):
        x = self._canvas.canvasx(event.x)
        y = self._canvas.canvasy(event.y)
        selected = self._sel_point.get()
        scale = 2 ** self._scale
        self._positions_data[selected].x = (x - 20) / scale
        self._positions_data[selected].y = (y - 20) / scale
        self._draw()

    def _canvas_mouse_motion(self, event):
        if not self._img:
            return

        x = self._canvas.canvasx(event.x) - 20
        y = self._canvas.canvasy(event.y) - 20
        scale = 2 ** self._scale
        x //= scale
        y //= scale
        pos = self._map_file.xy2latlon(x, y)
        self._status_x.config(text=f"x: {x}")
        self._status_y.config(text=f"y: {y}")
        lat = formatting.format_pos_lat(pos[0]) if pos else ""
        lon = formatting.format_pos_lon(pos[1]) if pos else ""
        self._status_lat.config(text=lat)
        self._status_lon.config(text=lon)
        self._status_zoom.config(text=f"{scale:0.2f}x")

    def _canvas_mouse_wheel(self, event):
        if (event.num == 5 or event.delta == -120) and self._scale > -5:
            self._scale -= 1
        elif (event.num == 4 or event.delta == 120) and self._scale < 1:
            self._scale += 1
        else:
            return

        self._load(self._img_filename)
        self._draw(True)
        self._canvas_mouse_motion(event)

    def _on_point_rb(self):
        selected = self._sel_point.get()
        x = self._positions_data[selected].x
        y = self._positions_data[selected].y
        if x is not None and y is not None:
            dx = float(x) / self._img.width()
            dy = float(y) / self._img.height()
            # center point on screen
            ddx = self._canvas.winfo_width() / 2.0 / self._img.width()
            ddy = self._canvas.winfo_height() / 2.0 / self._img.height()
            dx += -ddx if dx < 0.5 else ddx
            dy += -ddy if dy < 0.5 else ddy
            self._canvas.xview_moveto(max(min(dx, 1.0), 0.0))
            self._canvas.yview_moveto(max(min(dy, 1.0), 0.0))
            self._draw()

    def _draw(self, clear=False):
        self._busy_manager.busy()
        self.update()
        canvas = self._canvas
        if clear:
            canvas.delete("marker")

        scale = 2 ** self._scale
        for idx, point in enumerate(self._positions_data):
            if point.x is not None and point.y is not None:
                x, y = point.x * scale + 20, point.y * scale + 20

                p = self._positions_data[idx].marker
                if p and not clear:
                    canvas.coords(p[0], x, y - 20, x, y + 20)
                    canvas.coords(p[1], x - 20, y, x + 20, y)
                    canvas.coords(p[2], x + 12, y + 12)  # label
                    canvas.coords(p[3], x - 20, y - 20, x + 20, y + 20)
                    canvas.coords(p[4], x - 20, y - 20, x + 20, y + 20)
                    canvas.coords(p[5], x + 3, y + 3, x + 20, y + 20)
                else:
                    l1 = canvas.create_line(x, y - 20, x, y + 20, fill="red",
                                            tag="marker")
                    l2 = canvas.create_line(x - 20, y, x + 20, y, fill="red",
                                            tag="marker")
                    o = canvas.create_oval(x - 20, y - 20, x + 20, y + 20,
                                           activewidth="6", width="5",
                                           outline="black",
                                           tag="marker")
                    o2 = canvas.create_oval(x - 20, y - 20, x + 20, y + 20,
                                            activewidth="3", width="2",
                                            outline="red",
                                            tag="marker")
                    tb = canvas.create_oval(x + 3, y + 3, x + 20, y + 20,
                                            fill="white")
                    t = canvas.create_text(x + 12, y + 12, fill="red",
                                           text=str(idx + 1),
                                           tag="marker")
                    self._positions_data[idx].marker = (l1, l2, t, o, o2, tb)

        self._busy_manager.notbusy()
        self.update_idletasks()

    def _calibrate(self):
        for idx, p in enumerate(self._positions_data):
            if not p.validate():
                messagebox.showerror(
                    "Calibration error",
                    "Marker {idx + 1} not set or has invalid data")
                return

        if not self._img:
            messagebox.showerror("Error",
                                 "Please load image and calibrate map")
            return

        self._map_file.image_width = self._img.width()
        self._map_file.image_height = self._img.height()
        self._map_file.img_filename = self._img_filename
        self._map_file.img_filepath = os.path.dirname(self._img_filename)
        points = [mapfile.Point(x=p.x, y=p.y, lon=p.lon, lat=p.lat, idx=idx)
                  for idx, p in enumerate(self._positions_data)]
        self._map_file.set_points(points)
        self._map_file.calibrate()

        content = self._map_file.to_str()
        d = dialogs.TextDialog(
            self, "Calibrate completed; .map file content", content)
        self.wait_window(d)

    def _validate(self):
        if not self._img:
            messagebox.showerror("Error",
                                 "Please load image and calibrate map")
            return False

        if not self._map_file.validate():
            messagebox.showerror("Error", "Please calibrate map")
            return False

        return True
