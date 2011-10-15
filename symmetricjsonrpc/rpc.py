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

"""JSON-RPC implementation classes."""

from __future__ import with_statement

import select
import socket
import threading
import time
import traceback
import unittest

import dispatcher
import json

class ClientConnection(dispatcher.Connection):
    """A connection manager for a connected socket (or similar) that
    reads and dispatches JSON values."""

    def _init(self, subject, parent=None, *arg, **kw):
        self.reader = json.Reader(subject)
        self.writer = json.Writer(subject)
        dispatcher.Connection._init(self, subject=subject, parent=parent, *arg, **kw)

    def shutdown(self):
        self.reader.close()
        self.writer.close()
        dispatcher.Connection.shutdown(self)

    def read(self):
        return self.reader.read_values()

class RPCClient(ClientConnection):
    """A JSON RPC client connection manager.

    This class represents a single client-server connection on both
    the conecting and listening side. It provides methods for issuing
    requests and sending notifications, as well as handles incoming
    JSON RPC request, responses and notifications and dispatches them
    in separate threads.

    The dispatched threads are instances of RPCClient.Dispatch, and
    you must subclass it and override the dispatch_* methods in it to
    handle incoming data."""

    class Request(dispatcher.ThreadedClient):
        def dispatch(self, subject):
            if 'method' in subject and 'id' in subject:
                try:
                    result = self.dispatch_request(subject)
                    error = None
                except Exception, e:
                    result = None
                    error = {'type': type(e).__name__,
                             'args': list(e.args)}
                self.parent.respond(result, error, subject['id'])
            elif 'result' in subject or 'error' in subject:
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

    def _init(self, subject, parent=None, *arg, **kw):
        self._request_id = 0
        self._send_lock = threading.Lock()
        self._recv_waiting = {}
        ClientConnection._init(self, subject=subject, parent=parent, *arg, **kw)

    def request(self, method, params=[], wait_for_response=False, timeout=None):
        with self._send_lock:
            self._request_id += 1
            request_id = self._request_id
            if wait_for_response:
                self._recv_waiting[request_id] = {'condition': threading.Condition(), 'result': None}
            self.writer.write_value({'jsonrpc': '2.0', 'method': method, 'params': params, 'id': request_id})

            if not wait_for_response:
                return request_id

        try:
            with self._recv_waiting[request_id]['condition']:
                self._recv_waiting[request_id]['condition'].wait(timeout)
                if self._recv_waiting[request_id]['result'].has_key('error') and self._recv_waiting[request_id]['result']['error'] is not None:
                    exc = Exception(self._recv_waiting[request_id]['result']['error']['message'])
                    raise exc
                return self._recv_waiting[request_id]['result']['result']
        finally:
            del self._recv_waiting[request_id]

    def respond(self, result, error, id):
        with self._send_lock:
            self.writer.write_value({'result': result, 'error': error, 'id': id})

    def notify(self, method, params=[]):
        with self._send_lock:
            self.writer.write_value({'method': method, 'params': params})

    def __getattr__(self, name):
        def rpc_wrapper(*arg):
            return self.request(name, list(arg), wait_for_response=True)
        return rpc_wrapper

class RPCServer(dispatcher.ServerConnection):
    """A JSON RPC server connection manager. This class manages a
    listening sockets and recieves and dispatches new inbound
    connections. Each inbound connection is awarded two threads, one
    that can call the other side if there is a need, and one that
    handles incoming requests, responses and notifications.

    RPCServer.Dispatch.Dispatch is an RPCClient subclass that handles
    incoming requests, responses and notifications. Initial calls to
    the remote side can be done from its run_parent() method."""

    class InboundConnection(dispatcher.ThreadedClient):
        class Thread(RPCClient):
            def run_parent(self):
                """Server can call client from here..."""
                pass

class RPCP2PNode(dispatcher.ThreadedClient):
    class Thread(RPCServer):
        def run_parent(self):
            """Server can make connections from here by calling self.Dispatch()"""
            pass


################################ Unit-test code ################################

debug_tests = False

class TestEchoDispatcher(object):
    def __init__(self, subject, parent):
        if not hasattr(parent, "writer"):
            parent = parent.parent
        parent.writer.write_value(subject)

class TestEchoClient(ClientConnection):
    Request = TestEchoDispatcher

class TestThreadedEchoClient(ClientConnection):
    class Request(dispatcher.ThreadedClient):
        Thread = TestEchoDispatcher

class TestEchoServer(dispatcher.ServerConnection):
    InboundConnection = TestEchoClient

class TestThreadedEchoServer(dispatcher.ServerConnection):
    class InboundConnection(dispatcher.ThreadedClient):
        Thread = TestThreadedEchoClient

class TestPingRPCClient(RPCClient):
    class Request(RPCClient.Request):
        def dispatch_request(self, subject):
            if debug_tests: print "PingClient: dispatch_request", subject
            assert subject['method'] == "pingping"
            return "pingpong"

class TestPongRPCServer(RPCServer):
    class InboundConnection(RPCServer.InboundConnection):
        class Thread(RPCServer.InboundConnection.Thread):
            class Request(RPCServer.InboundConnection.Thread.Request):
                def dispatch_request(self, subject):
                    if debug_tests: print "TestPongRPCServer: dispatch_request", subject
                    assert subject['method'] == "ping"
                    assert self.parent.request("pingping", wait_for_response=True) == "pingpong"
                    if debug_tests: print "TestPongRPCServer: back-pong"
                    return "pong"

class TestPongRPCP2PServer(RPCP2PNode):
    class Thread(RPCP2PNode.Thread):
        class InboundConnection(RPCP2PNode.Thread.InboundConnection):
            class Thread(RPCP2PNode.Thread.InboundConnection.Thread):
                class Request(RPCP2PNode.Thread.InboundConnection.Thread.Request):
                    def dispatch_request(self, subject):
                        if debug_tests: print "TestPongRPCP2PServer: dispatch_request", subject
                        if subject['method'] == "ping":
                            assert self.parent.request("pingping", wait_for_response=True) == "pingpong"
                            if debug_tests: print "TestPongRPCServer: back-pong"
                            return "pong"
                        elif subject['method'] == "pingping":
                            if debug_tests: print "PingClient: dispatch_request", subject
                            return "pingpong"
                        else:
                            assert False
        def run_parent(self):
            client = self.InboundConnection.Thread(test_make_client_socket())
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
    return s

class TestRpc(unittest.TestCase):
    def test_client(self):
        sockets = socket.socketpair()
        echo_server = TestEchoClient(sockets[1])

        reader = json.Reader(sockets[0])
        writer = json.Writer(sockets[0])

        obj = {'foo':1, 'bar':[1, 2]}
        writer.write_value(obj)
        return_obj = reader.read_value()
        self.assertEqual(obj, return_obj)

    def test_return_on_closed_socket(self):
        server_socket = test_make_server_socket()
        echo_server = TestEchoServer(server_socket, name="TestEchoServer")

        client_socket = test_make_client_socket()
        writer = json.Writer(client_socket)
        writer.write_value({'foo':1, 'bar':2})
        client_socket.close()

        echo_server.shutdown()
        echo_server.join()

    def test_server(self):
        for n in range(3):
            server_socket = test_make_server_socket()
            echo_server = TestEchoServer(server_socket, name="TestEchoServer")

            client_socket = test_make_client_socket()
            reader = json.Reader(client_socket)
            writer = json.Writer(client_socket)

            obj = {'foo':1, 'bar':[1, 2]}
            writer.write_value(obj)
            return_obj = reader.read_value()

            self.assertEqual(obj, return_obj)
            echo_server.shutdown()
            echo_server.join()

    def test_threaded_server(self):
        for n in range(3):
            server_socket = test_make_server_socket()
            echo_server = TestThreadedEchoServer(server_socket, name="TestEchoServer")

            client_socket = test_make_client_socket()
            writer = json.Writer(client_socket)

            obj = {'foo':1, 'bar':[1, 2]}
            writer.write_value(obj)

            reader = json.Reader(client_socket)
            return_obj = reader.read_value()

            self.assertEqual(obj, return_obj)
            echo_server.shutdown()
            echo_server.join()

    def test_rpc_server(self):
        for n in range(3):
            server_socket = test_make_server_socket()
            server = TestPongRPCServer(server_socket, name="PongServer")

            client_socket = test_make_client_socket()
            client = TestPingRPCClient(client_socket)
            self.assertEqual(client.request("ping", wait_for_response=True), "pong")
            self.assertEqual(client.ping(), "pong")
            server.shutdown()
            server.join()

    def test_rpc_p2p_server(self):
        for n in range(3):
            server_socket = test_make_server_socket()
            res = {}
            server = TestPongRPCP2PServer(server_socket, res, name="PongServer")
            for x in xrange(0, 4):
                if 'result' in res:
                    break
                time.sleep(1)
            assert 'result' in res and res['result']

            server.shutdown()
            server.join()

if __name__ == "__main__":
    unittest.main()
