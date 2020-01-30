#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © Karol Będkowski, 2020
#
# This file is part of tbviewer
# Distributed under terms of the GPLv3 license.

"""Common tk dialogs."""

import tkinter as tk


class TextDialog(tk.Toplevel):
    """Simple dialog with text content and ok button."""

    def __init__(self, parent, header, text):
        """Create text dialog.

        :param parent: parent widget
        :param header: header text
        :param text: text to display
        """
        tk.Toplevel.__init__(self, parent)
        self.transient(parent)

        tk.Label(self, text=header).pack()
        etxt = self._txt = tk.Text(self, wrap=tk.NONE)
        etxt.pack(padx=5, fill=tk.BOTH, expand=1)
        etxt.insert(tk.END, text)
        etxt.config(state=tk.DISABLED)

        tk.Button(self, text="OK", command=self._ok).pack(pady=5)

    def _ok(self):
        self.destroy()
