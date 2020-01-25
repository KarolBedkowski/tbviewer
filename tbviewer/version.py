#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Copyright © Karol Będkowski, 2015-2020
#
# This file is part of tbviewer
# Distributed under terms of the GPLv3 license.

"""Licence and version informations."""


import gettext

_ = gettext.gettext

SHORTNAME = "tbviewer"
NAME = _("tbviewer")
VERSION = "0.2.1"
VERSION_INFO = (0, 2, 2, "alpha", 1)
RELEASE = "2015-09-30"
DESCRIPTION = _("""tbviewer""")
DEVELOPERS = u"""Karol Będkowski"""
TRANSLATORS = u"""Karol Będkowski"""
COPYRIGHT = u"Copyright (c) Karol Będkowski, 2015-2020"
LICENSE = _("""\
This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
""")


INFO = _("""\
%(name)s version %(version)s (%(release)s)
%(copyright)s

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

For details please see COPYING file.
""") % dict(name=NAME, version=VERSION, copyright=COPYRIGHT, release=RELEASE)
