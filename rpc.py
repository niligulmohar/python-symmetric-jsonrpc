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

import json, dispatcher, threading, traceback, unittest, socket, time, select

class ClientConnection(dispatcher.Connection):
    """A connection manager for a connected socket (or similar) that
    reads and dispatches JSON values."""

    def _init(self, subject, *arg, **kw):
        self.reader = json.ParserReader(subject)
        self.writer = json.Writer(subject)
        dispatcher.Connection._init(self, subject, *arg, **kw)

    def read(self):
        # FIXME: How to handle shutdown here?
        return self.reader.read_values()

class RPCClient(ClientConnection):
    """A JSON RCP client connection manager. This class represents a
    single client-server connection on both the conecting and
    listening side. It provides methods for issuing requests and
    sending notifications, as well as handles incoming JSON RPC
    request, responses and notifications and dispatches them in
    separate threads. The dispatched threads are instances of
    RPCClient.Dispatch, and you must subclass it and override the
    dispatch_* methods in it to handle incoming data."""

    class Dispatch(dispatcher.ThreadedClient):
        def dispatch(self, subject):
            if 'method' in subject and 'id' in subject:
                try:
                    result = self.dispatch_request(subject)
                    error = None
                except Exception, e:
                    result = None
                    error = {'type': type(e).__name__,
                             'args': e.args}
                self.parent.respond(result, error, subject['id'])
            elif 'result' in subject:
                assert 'id' in subject
                if subject['id'] in self.parent._recv_waiting:
                    with self.parent._recv_waiting[subject['id']]['condition']:
                        self.parent._recv_waiting[subject['id']]['result'] = subject
                        self.parent._recv_waiting[subject['id']]['condition'].notifyAll()
                else:
                    self.dispatch_response(subject)
                
            elif 'method' in subject:
                try:
                    self.dispatch_notification(subject)
                except:
                    traceback.print_exc()

        def dispatch_request(self, subject):
            pass

        def dispatch_notification(self, subject):
            pass

        def dispatch_response(self, subject):
            """Note: Only used to results for calls that some other thread isn't waiting for"""
            pass

    def _init(self, *arg, **kw):
        self._request_id = 0
        self._send_lock = threading.Lock()
        self._recv_waiting = {}
        ClientConnection._init(self, *arg, **kw)

    def request(self, method, params = [], wait_for_response = False):
        with self._send_lock:
            self._request_id += 1
            request_id = self._request_id
            if wait_for_response:
                self._recv_waiting[request_id] = {'condition':threading.Condition(), 'result': None}
            self.writer.write_value({'method':method, 'params': params, 'id': request_id})
            self.subject.flush()

            if not wait_for_response:
                return request_id

        try:
            with self._recv_waiting[request_id]['condition']:
                self._recv_waiting[request_id]['condition'].wait()
                if self._recv_waiting[request_id]['result']['error'] is not None:
                    raise Exception(self._recv_waiting[request_id]['result']['error']['args'],
                                    serialized_type = self._recv_waiting[request_id]['result']['error']['type'])
                return self._recv_waiting[request_id]['result']['result']
        finally:
            del self._recv_waiting[request_id]


    def respond(self, result, error, id):
        with self._send_lock:
            self.writer.write_value({'result':result, 'error': error, 'id': id})
            self.subject.flush()

    def notify(self, method, params = []):
        with self._send_lock:
            self.writer.write_value({'method':method, 'params': params})
            self.subject.flush()

class RPCServer(dispatcher.ServerConnection):
    """A JSON RPC server connection manager. This class manages a
    listening sockets and recieves and dispatches new inbound
    connections. Each inbound connection is awarded two threads, one
    that can call the other side if there is a need, and one that
    handles incoming requests, responses and
    notifications.

    RPCServer.Dispatch.Dispatch is an RPCClient subclass that handles
    incoming requests, responses and notifications. Initial calls to
    the remote side can be done from its run_parent() method."""

    class Dispatch(dispatcher.ThreadedClient):
        class Dispatch(RPCClient):
            def run_parent(self):
                """Server can call client from here..."""
                pass

class RPCP2PNode(dispatcher.ThreadedClient):
    class Dispatch(RPCServer):
        def run_parent(self):
            """Server can make connections from here by calling self.Dispatch()"""
            pass


################################ Unit-test code ################################

class EchoDispatcher(object):
    def __init__(self, subject, parent):
        json.Writer(parent.subject).write_value(subject)
        parent.subject.flush()

class EchoClient(ClientConnection):
    Dispatch = EchoDispatcher

class ThreadedEchoClient(ClientConnection):
    class Dispatch(dispatcher.ThreadedClient):
        Dispatch = EchoDispatcher

class EchoServer(dispatcher.ServerConnection):
    Dispatch = EchoClient

class ThreadedEchoServer(dispatcher.ServerConnection):
    class Dispatch(dispatcher.ThreadedClient):
        Dispatch = ThreadedEchoClient

class PingRPCClient(RPCClient):
    class Dispatch(RPCClient.Dispatch):
        def dispatch_request(self, subject):
            print "PingClient: dispatch_request", subject
            assert subject['method'] == "pingping"
            return "pingpong"    

class PongRPCServer(RPCServer):
    class Dispatch(RPCServer.Dispatch):
        class Dispatch(RPCServer.Dispatch.Dispatch):
            class Dispatch(RPCServer.Dispatch.Dispatch.Dispatch):
                def dispatch_request(self, subject):
                    print "PongRPCServer: dispatch_request", subject
                    assert subject['method'] == "ping"
                    assert self.parent.request("pingping", wait_for_response=True) == "pingpong"
                    print "PongRPCServer: back-pong"
                    return "pong"

class PongRPCP2PServer(RPCP2PNode):
    class Dispatch(RPCP2PNode.Dispatch):
        class Dispatch(RPCP2PNode.Dispatch.Dispatch):
            class Dispatch(RPCP2PNode.Dispatch.Dispatch.Dispatch):
                class Dispatch(RPCP2PNode.Dispatch.Dispatch.Dispatch.Dispatch):
                    def dispatch_request(self, subject):
                        print "PongRPCP2PServer: dispatch_request", subject
                        if subject['method'] == "ping":
                            assert self.parent.request("pingping", wait_for_response=True) == "pingpong"
                            print "PongRPCServer: back-pong"
                            return "pong"
                        elif subject['method'] == "pingping":
                            print "PingClient: dispatch_request", subject
                            return "pingpong"
                        else:
                            assert False
        def run_parent(self):
            client = self.Dispatch.Dispatch(test_make_client_socket())
            self.parent.parent['result'] = client.request("ping", wait_for_response=True) == "pong"

def test_make_server_socket():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('', 4712))
    s.listen(1)
    return s

def test_make_client_socket():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(('localhost', 4712))
    return s.makefile('r+')

class TestRpc(unittest.TestCase):
    def test_client(self):
        sockets = [s.makefile('r+') for s in socket.socketpair()]
        reader = json.ParserReader(sockets[0])
        writer = json.Writer(sockets[0])
        echo_server = EchoClient(sockets[1])

        obj = {'foo':1, 'bar':[1, 2]}
        writer.write_value(obj)
        return_obj = reader.read_value()

        self.assertEqual(obj, return_obj)

    def no_test_return_on_closed_socket(self):
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind(('', 4712))
            server_socket.listen(1)
            echo_server = EchoServer(server_socket, name="EchoServer")

            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect(('localhost', 4712))
            client_socket = client_socket.makefile('r+')

            print json_string
            client_socket.write(json_string)
            client_socket.close()

            echo_server.shutdown()

    def test_server(self):
        for n in range(3):
            server_socket = test_make_server_socket()
            echo_server = EchoServer(server_socket, name="EchoServer")

            client_socket = test_make_client_socket()
            writer = json.Writer(client_socket)

            obj = {'foo':1, 'bar':[1, 2]}
            writer.write_value(obj)
            client_socket.flush()

            reader = json.ParserReader(client_socket)
            return_obj = reader.read_value()

            self.assertEqual(obj, return_obj)
            echo_server.shutdown()

    def test_threaded_server(self):
        for n in range(3):
            server_socket = test_make_server_socket()
            echo_server = ThreadedEchoServer(server_socket, name="EchoServer")

            client_socket = test_make_client_socket()
            writer = json.Writer(client_socket)

            obj = {'foo':1, 'bar':[1, 2]}
            writer.write_value(obj)
            client_socket.flush()

            reader = json.ParserReader(client_socket)
            return_obj = reader.read_value()

            self.assertEqual(obj, return_obj)
            echo_server.shutdown()

    def test_rpc_server(self):
        for n in range(3):
            server_socket = test_make_server_socket()
            server = PongRPCServer(server_socket, name="PongServer")

            client_socket = test_make_client_socket()
            client = PingRPCClient(client_socket)
            self.assertEqual(client.request("ping", wait_for_response=True), "pong")
            server.shutdown()

    def test_rpc_p2p_server(self):
        #for n in range(3):
            server_socket = test_make_server_socket()
            res = {}
            server = PongRPCP2PServer(server_socket, res, name="PongServer")
            server.join()
            assert res['result']
            server.shutdown()

if __name__ == "__main__":
    unittest.main()
