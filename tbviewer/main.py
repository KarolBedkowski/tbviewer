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


from tbviewer import version


def _parse_opt():
    """ Parse cli options. """
    optp = optparse.OptionParser(version=version.NAME + version.VERSION)
    group = optparse.OptionGroup(optp, "Debug options")
    group.add_option("--debug", "-d", action="store_true", default=False,
                     help="enable debug messages")
    group.add_option("--shell", action="store_true", default=False,
                     help="start shell")
    optp.add_option_group(group)
    return optp.parse_args()[0]


def run():
    """ Run application. """
    # parse options
    options = _parse_opt()

    # logowanie
    from tbviewer.lib.logging_setup import logging_setup
    logging_setup("tbviewer.log", options.debug)

    # app config
    from tbviewer.lib import appconfig
    config = appconfig.AppConfig("tbviewer.cfg", "tbviewer")
    config.load_defaults(config.get_data_file("defaults.cfg"))
    config.load()
    config.debug = options.debug

    # locale
    from tbviewer.lib import locales
    locales.setup_locale(config)

    if options.shell:
        # starting interactive shell
        from IPython.terminal import ipapp
        app = ipapp.TerminalIPythonApp.instance()
        app.initialize(argv=[])
        app.start()
        return

    from tbviewer.gui import wnd_main

    window = wnd_main.WndMain()
    window.mainloop()

    config.save()
