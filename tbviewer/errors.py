#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © Karol Będkowski, 2020
#
# This file is part of tbviewer
# Distributed under terms of the GPLv3 license.

"""Common application errors."""


class InvalidFileException(RuntimeError):
    """Error generated when loaded file is invalid for some reason."""
