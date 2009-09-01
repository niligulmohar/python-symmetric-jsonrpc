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

import symmetricjsonrpc, socket

class PingRPCClient(symmetricjsonrpc.RPCClient):
    class Request(symmetricjsonrpc.RPCClient.Request):
        def dispatch_request(self, subject):
            # Handle callbacks from the server
            assert subject['method'] == "pingping"
            return "pingpong"    

# Set up a TCP socket and connect to the server
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(('localhost', 4712))

# Create a client thread handling for incoming requests
client = PingRPCClient(s)

# Call a method on the server
assert client.request("ping", wait_for_response=True) == "pong"

# Notify server it can shut down
client.notify("shutdown")

client.shutdown()
