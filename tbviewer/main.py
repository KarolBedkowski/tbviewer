# -*- coding: utf-8 -*-
""" Main module.

Copyright (c) Karol Będkowski, 2015

This file is part of tbviewer
Licence: GPLv2+
"""

__author__ = "Karol Będkowski"
__copyright__ = "Copyright (c) Karol Będkowski, 2015"
__version__ = "2015-05-10"

import optparse
import logging

_LOG = logging.getLogger(__name__)


from . import version


def _parse_opt():
    """ Parse cli options. """
    optp = optparse.OptionParser(version=version.NAME + version.VERSION)
    group = optparse.OptionGroup(optp, "Debug options")
    group.add_option("--debug", "-d", action="store_true", default=False,
                     help="enable debug messages")
    group.add_option("--shell", action="store_true", default=False,
                     help="start shell")
    optp.add_option_group(group)
    return optp.parse_args()


def run():
    """ Run application. """
    # parse options
    options, args = _parse_opt()

    # logowanie
    from .logging_setup import logging_setup
    logging_setup("tbviewer.log", options.debug)

    if options.shell:
        # starting interactive shell
        from IPython.terminal import ipapp
        app = ipapp.TerminalIPythonApp.instance()
        app.initialize(argv=[])
        app.start()
        return

    from . import wnd_main

    fname = None
    if args and args[0]:
        fname = args[0]

    window = wnd_main.WndMain(fname)
    window.mainloop()
