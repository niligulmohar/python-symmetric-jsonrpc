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

class PongRPCServer(symmetricjsonrpc.RPCServer):
    class InboundConnection(symmetricjsonrpc.RPCServer.InboundConnection):
        class Thread(symmetricjsonrpc.RPCServer.InboundConnection.Thread):
            class Request(symmetricjsonrpc.RPCServer.InboundConnection.Thread.Request):
                def dispatch_notification(self, subject):
                    assert subject['method'] == "shutdown"
                    # Shutdown the server. Note: We must use a
                    # notification, not a method for this - when the
                    # server's dead, there's no way to inform the
                    # client that it is...
                    symmetricjsonrpc.ShutDownThread(self.parent.parent.parent)

                def dispatch_request(self, subject):
                    assert subject['method'] == "ping"
                    # Call the client back
                    # self.parent is a symmetricjsonrpc.RPCClient subclass (see the client code for more examples)
                    assert self.parent.request("pingping", wait_for_response=True) == "pingpong"
                    return "pong"
                    
# Set up a TCP socket and start listening on it for connections
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(('', 4712))
s.listen(1)

# Create a server thread handling incoming connections
server = PongRPCServer(s, name="PongServer")

# Wait for the server to stop serving clients
server.join()
