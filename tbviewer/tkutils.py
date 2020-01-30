#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © Karol Będkowski, 2020
#
# This file is part of tbviewer
# Distributed under terms of the GPLv3 license.

"""Various utilities for tk."""

import tkinter as tk


class BusyManager:
    """Control busy state for root widget and all it children.

    Based on: https://effbot.org/zone/tkinter-busy.htm
    """

    def __init__(self, root):
        """Create BusyManager for `root` widget."""
        self._root = root
        self._busy_widgets = {}

    def busy(self, widget=None):
        """Set busy state."""
        widget = widget or self._root

        if id(widget) not in self._busy_widgets:
            try:
                if widget.cget("cursor") != "clock":
                    self._busy_widgets[id(widget)] = widget
                    widget.config(cursor="watch")
            except tk.TclError:
                pass

        for child in widget.children.values():
            self.busy(child)

    def notbusy(self):
        """Set not busy state for all changed previously widgets."""
        for widget in self._busy_widgets.values():
            try:
                widget.config(cursor="")
            except tk.TclError:
                pass
        self._busy_widgets.clear()
