#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright (c) Karol Będkowski, 2015-2020
#
# This file is part of tbviewer
# Distributed under terms of the GPLv3 license.

"""Various common formatting data functions."""

import math
import locale


def format_pos(degree, latitude=True, short=True):
    lit = ["EW", "NS"][0 if latitude else 1][0 if degree > 0 else 1]
    degree = abs(degree)
    mint, stop = math.modf(degree)
    if short:
        return "%d° %s' %s" % (
            stop, locale.format('%00.2f', mint * 60), lit)
    sec, mint = math.modf(mint * 60)
    return "%d° %d' %s'' %s" % (
        stop, mint, locale.format('%00.2f', sec * 60), lit)


def format_pos_lon(degree, short=True):
    return format_pos(degree, False, short)


def format_pos_lat(degree, short=True):
    return format_pos(degree, True, short)


def format_pos_latlon(lat, lon, short=True):
    return format_pos(lat, False, short) + "       " + \
        format_pos(lon, True, short)


def prettydict(d):
    return "{" + ";  ".join(
        str(key) + "=" + repr(val)
        for key, val in sorted(d.items())
    ) + "}"
