#!/usr/bin/python3
# -*- coding: utf-8 -*-
""" Logging setup.
Copyright (c) Karol Będkowski, 2015

This file is part of tbviewer
Licence: GPLv2+
"""
__author__ = "Karol Będkowski"
__copyright__ = "Copyright (c) Karol Będkowski, 2015"
__version__ = "2015-05-12"

import sys
import os.path
import logging


class ColorFormatter(logging.Formatter):
    """ Formatter for logs that color messages according to level. """
    FORMAT_MAP = {level: ("\033[1;%dm%s\033[0m" % (color, level))
                  for level, color in
                  (("DEBUG", 34), ("INFO", 37), ("WARNING", 33), ("ERROR", 31),
                   ("CRITICAL", 31))}

    def format(self, record):
        record.levelname = self.FORMAT_MAP.get(record.levelname,
                                               record.levelname)
        return logging.Formatter.format(self, record)


def logging_setup(filename, debug=False):
    """ Setup configuration.

    Args:
        filename: log file name
        debug: (bool) set more messages
    """
    log_fullpath = os.path.abspath(filename)

    if debug:
        sys.stderr.write("Logging to %s" % log_fullpath)

    if debug:
        level_console = logging.DEBUG
        level_file = logging.DEBUG
    else:
        level_console = logging.INFO
        level_file = logging.ERROR

    logging.basicConfig(level=level_file,
                        format="%(asctime)s %(levelname)-8s %(name)s "
                        "- %(message)s",
                        filename=log_fullpath, filemode="w")
    console = logging.StreamHandler()
    console.setLevel(level_console)

    fmtr = logging.Formatter
    if sys.platform != "win32":
        fmtr = ColorFormatter
    console.setFormatter(fmtr("%(levelname)-8s %(name)s - %(message)s"))
    logging.getLogger("").addHandler(console)

    log = logging.getLogger(__name__)
    log.debug("logging_setup() finished")
