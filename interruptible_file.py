#! /bin/env python
# -*- coding: UTF-8 -*-
# vim: set fileencoding=UTF-8 :

# python-symmetric-jsonrcp
# Copyright (C) 2009 Egil Moeller <redhog@redhog.org>
# Copyright (C) 2009 Nicklas Lindgren <nili@gulmohar.se>

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

from __future__ import with_statement

import select

class InterruptibleFile(object):
    def __init__(self, file):
        self.closed = false
        self.file = file
        self.poll_rd = select.poll()
        self.poll_rd.register(file, select.POLLIN | select.POLLPRI | select.POLLERR | select.POLLHUP | select.POLLNVAL)
        self.poll_wr = select.poll()
        self.poll_wr.register(file, select.POLLOUT | select.POLLERR | select.POLLHUP | select.POLLNVAL)

    def close():
        self.closed = True
        self.file.close()

    def flush():
        self.file.flush()

    def fileno():
        return self.file.fileno()

    def isatty():
        return self.file.isatty()

    def next():
        pass
    
    def read(size = 0):
        pass
    
    def readline([size]):
        pass
    def readlines([sizehint]):
        pass
    def xreadlines():
        pass
    def seek(offset[, whence]):
        pass
    def tell():
        pass
    def truncate([size]):
        pass
    def write(str):
        pass
    def writelines(sequence):
        pass

    @property
    def encoding(self):
        return self.file.encoding

    @property # Add writable attribute
    def errors(self):
        return self.file.errors

    @property
    def mode(self):
        return self.file.mode

    @property
    def name(self):
        return self.file.name
    
    @property
    def newlines(self):
        return self.file.newlines
