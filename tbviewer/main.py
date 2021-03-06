# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © Karol Będkowski, 2015-2020
#
# This file is part of tbviewer
# Distributed under terms of the GPLv3 license.

"""Main module."""

import optparse
import logging
import tempfile
import time
import os

from . import version

_LOG = logging.getLogger(__name__)


def _parse_opt():
    """Parse cli options."""
    optp = optparse.OptionParser(version=version.NAME + version.VERSION)
    group = optparse.OptionGroup(optp, "Debug options")
    group.add_option("--debug", "-d", action="store_true", default=False,
                     help="enable debug messages")
    group.add_option("--shell", action="store_true", default=False,
                     help="start shell")
    optp.add_option_group(group)
    return optp.parse_args()


def run_viewer():
    """Run viewer application."""
    # parse options
    options, args = _parse_opt()

    # logowanie
    from .logging_setup import logging_setup
    logdir = tempfile.mkdtemp("_log_" + str(int(time.time())), "tbviewer_")
    logging_setup(os.path.join(logdir, "tbviewer.log"), options.debug)

    if options.shell:
        # starting interactive shell
        from IPython.terminal import ipapp
        app = ipapp.TerminalIPythonApp.instance()
        app.initialize(argv=[])
        app.start()
        return

    from . import wnd_viewer

    fname = args[0] if args and args[0] else None

    window = wnd_viewer.WndViewer(fname)
    window.mainloop()


def run_calibrate():
    """Run application."""
    # parse options
    options, args = _parse_opt()

    # logowanie
    from .logging_setup import logging_setup
    logdir = tempfile.mkdtemp("_log_" + str(int(time.time())), "tbviewer_")
    logging_setup(os.path.join(logdir, "tbviewer.log"), options.debug)

    if options.shell:
        # starting interactive shell
        from IPython.terminal import ipapp
        app = ipapp.TerminalIPythonApp.instance()
        app.initialize(argv=[])
        app.start()
        return

    from . import wnd_calibrate

    fname = args[0] if args else None
    mapfname = args[1] if args and len(args) > 1 else None

    window = wnd_calibrate.WndCalibrate(fname, mapfname)
    window.mainloop()
