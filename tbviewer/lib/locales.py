# -*- coding: utf-8 -*-

""" Locale support functions.

Copyright (c) Karol Będkowski, 2013-2014

This file is part of exifeditor
Licence: GPLv2+
"""

__author__ = "Karol Będkowski"
__copyright__ = "Copyright (c) Karol Będkowski, 2014"
__version__ = "2014-12-27"


import os
import locale
import logging


_LOG = logging.getLogger(__name__)


def setup_locale(app_config):
    """ setup locales """
    locales_dir = app_config.locales_dir
    package_name = 'exifeditor'
    _LOG.info('run: locale dir: %s', locales_dir)
    try:
        locale.bindtextdomain(package_name, locales_dir)
        locale.bind_textdomain_codeset(package_name, "UTF-8")
    except AttributeError:
        pass
    default_locale = locale.getdefaultlocale()
    locale.setlocale(locale.LC_ALL, '')
    os.environ['LC_ALL'] = os.environ.get('LC_ALL') or default_locale[0]
    _LOG.info('locale: %s', str(locale.getlocale()))
