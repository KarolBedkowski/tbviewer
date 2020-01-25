#!/usr/bin/python3
# -*- coding: utf-8 -*-
# Copyright (c) Karol Będkowski, 2015-2020
#
# This file is part of tbviewer
# Distributed under terms of the GPLv3 license.

"""Logging setup."""

import sys
import os.path
import logging


class ColorFormatter(logging.Formatter):
    """Formatter for logs that color messages according to level."""

    FORMAT_MAP = {level: ("\033[1;%dm%s\033[0m" % (color, level))
                  for level, color in
                  (("DEBUG", 34), ("INFO", 37), ("WARNING", 33), ("ERROR", 31),
                   ("CRITICAL", 31))}

    def format(self, record):
        record.levelname = self.FORMAT_MAP.get(record.levelname,
                                               record.levelname)
        return logging.Formatter.format(self, record)


def logging_setup(filename, debug=False):
    """Configure global logger.

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
