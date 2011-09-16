#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim: set fileencoding=UTF-8 :

# python-symmetric-jsonrpc
# Copyright (C) 2009 Egil Moeller <redhog@redhog.org>
# Copyright (C) 2009 Nicklas Lindgren <nili@gulmohar.se>

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# Lesser General Public License for more details.

# You should have received a copy of the GNU Lesser General Public
# License along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
# USA

import sys, threading

if '--help' in sys.argv:
    print """client.py
    --ssl
        Encrypt communication with SSL using M2Crypto. Requires a
        server.pem and server.key in the current directory.
"""
    sys.exit(0)

if '--ssl' in sys.argv:
    # Set up a SSL socket
    import M2Crypto
    ctx = M2Crypto.SSL.Context()
    ctx.load_cert('server.pem', 'server.key')
    s = M2Crypto.SSL.Connection(ctx)
else:
    # Set up a TCP socket
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

#  Start listening on the socket for connections
s.bind(('', 4712))
s.listen(1)

s2 = s.accept()[0]

data = s2.recv()
while data:
    print repr(data)
    s2.send(data)
    data = s2.recv()
