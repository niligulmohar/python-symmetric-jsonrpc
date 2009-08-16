import json, threading, unittest, socket, time, select

class Thread(threading.Thread):
    debug_thread = False

    def __init__(self, *arg, **kw):
        self._init(*arg, **kw)
        self.start()
        self.run_parent()

    def _init(self, subject, parent = None, *arg, **kw):
        self.subject = subject
        self.parent = parent
        self._shutdown = False
        if 'name' not in kw:
            if self.parent:
                kw['name'] = "%s/%s" % (self.parent.getName(), type(self).__name__)
            else:
                kw['name'] = type(self).__name__
        threading.Thread.__init__(self, *arg, **kw)

    def run(self, *arg, **kw):
        if self.debug_thread: print "%s: BEGIN" % self.getName()
        self.run_thread(*arg, **kw)
        if self.debug_thread: print "%s: END" % self.getName()

    def shutdown(self):
        self._shutdown = True
        self.join()

    def run_parent(self):
        pass

    def run_thread(self, *arg, **kw):
        pass

class Connection(Thread):
    debug_dispatch = False

    class Dispatch(Thread): pass

    def run_thread(self):
        for value in self.read():
            if self.debug_dispatch: print "%s: DISPATCH: %s" % (self.getName(), value)
            self.dispatch(value)
            if self.debug_dispatch: print "%s: DISPATCH DONE: %s" % (self.getName(), value)

    def read(self):
        pass

    def dispatch(self, subject):
        self.Dispatch(parent = self, subject = subject)

class ClientConnection(Connection):
    def _init(self, subject, *arg, **kw):
        self.reader = json.ParserReader(subject)
        Connection._init(self, subject, *arg, **kw)

    def read(self):
        # FIXME: How to handle shutdown here?
        return self.reader.read_values()

class ServerConnection(Connection):
    Dispatch = ClientConnection

    def read(self):
        poll = select.poll()
        poll.register(self.subject, select.POLLIN)

        while True:
            status = poll.poll(100)
            if self._shutdown:
                self.subject.close()
                return
            if status:
                socket, address = self.subject.accept()
                yield socket.makefile('r+')

class ThreadedClient(Thread):
    Dispatch = ClientConnection

    def _init(self, *arg, **kw):
        Thread._init(self, *arg, **kw)
        self.dispatch_subject = self.subject
        self.subject = self.parent.subject

    def run_thread(self):
        self.dispatch(self.dispatch_subject)

    def dispatch(self, subject):
        self.Dispatch(parent = self, subject = subject)

class RPCClient(ClientConnection):
    class Dispatch(ThreadedClient):
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
                self.dispatch_notification(subject)

        def dispatch_request(self, subject):
            pass

        def dispatch_notification(self, subject):
            pass

        def dispatch_response(self, subject):
            # Note: Only used to results for calls that some other thread isn't waiting for
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
            json.json({'method':method, 'params': params, 'id': request_id}, self.subject)
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
            json.json({'result':result, 'error': error, 'id': id}, self.subject)
            self.subject.flush()

    def notify(self, method, params = []):
        with self._send_lock:            
            json.json({'method':method, 'params': params}, self.subject)
            self.subject.flush()

class RPCServer(ServerConnection):
    class Dispatch(ThreadedClient):
        class Dispatch(RPCClient):
            def run_parent(self):
                # Server can call client from here...
                pass

class EchoDispatcher(object):
    def __init__(self, subject, parent):
        json.json(subject, parent.subject)
        parent.subject.flush()

class EchoClient(ClientConnection):
    Dispatch = EchoDispatcher

class ThreadedEchoClient(ClientConnection):
    class Dispatch(ThreadedClient):
        Dispatch = EchoDispatcher

class EchoServer(ServerConnection):
    Dispatch = EchoClient

class ThreadedEchoServer(ServerConnection):
    class Dispatch(ThreadedClient):
        Dispatch = ThreadedEchoClient

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

class PingRPCClient(RPCClient):
    class Dispatch(RPCClient.Dispatch):
        def dispatch_request(self, subject):
            print "PingClient: dispatch_request", subject
            assert subject['method'] == "pingping"
            return "pingpong"    

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

class TestConnection(unittest.TestCase):
    def test_client(self):
        sockets = [s.makefile('r+') for s in socket.socketpair()]
        reader = json.ParserReader(sockets[0])
        echo_server = EchoClient(sockets[1])

        obj = {'foo':1, 'bar':[1, 2]}
        json.json(obj, sockets[0])
        return_obj = reader.read_value()

        self.assertEqual(obj, return_obj)

    def test_broken_socket(self):
        sockets = [s.makefile('r+') for s in socket.socketpair()]
        reader = json.ParserReader(sockets[0])

        sockets[0].close()

        self.assertRaises(ValueError, lambda: reader.read_value())

    def test_eof(self):
        import cStringIO

        obj = {'foo':1, 'bar':[1, 2]}
        io0 = cStringIO.StringIO()
        json.json(obj, io0)
        full_json_string = io0.getvalue()

        for json_string, eof_error in ((full_json_string, False), (full_json_string[0:10], True), ('', True)):
            io1 = cStringIO.StringIO(json_string)
            reader = json.ParserReader(io1)
            if eof_error:
                self.assertRaises(EOFError, lambda: reader.read_value())
            else:
                self.assertEqual(obj, reader.read_value())

    def test_closed_socket(self):
        class Timeout(threading.Thread):
            def run(self1):
                import cStringIO

                obj = {'foo':1, 'bar':[1, 2]}
                io = cStringIO.StringIO()
                json.json(obj, io)
                full_json_string = io.getvalue()

                for json_string, eof_error in ((full_json_string, False), (full_json_string[0:10], True), ('', True)):
                    sockets = [s.makefile('r+') for s in socket.socketpair()]
                    reader = json.ParserReader(sockets[0])

                    sockets[1].write(json_string)
                    sockets[1].close()
                    if eof_error:
                        self.assertRaises(EOFError, lambda: reader.read_value())
                    else:
                        self.assertEqual(obj, reader.read_value())

        timeout = Timeout()
        timeout.start()
        timeout.join(3)
        if timeout.isAlive():
            self.fail('Reader has hung.')

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
            
            obj = {'foo':1, 'bar':[1, 2]}
            json.json(obj, client_socket)
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

            obj = {'foo':1, 'bar':[1, 2]}
            json.json(obj, client_socket)
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

if __name__ == "__main__":
    unittest.main()
