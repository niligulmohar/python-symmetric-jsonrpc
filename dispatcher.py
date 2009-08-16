import json, threading, unittest, socket, time, select

debug_dispatch = True
debug_thread = True

class Thread(threading.Thread):
    def __init__(self, *arg, **kw):
        self._init(*arg, **kw)
        self.start()

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
        if debug_thread: print "%s: BEGIN" % (self.getName(), ) 
        self.run_thread(*arg, **kw)
        if debug_thread: print "%s: END" % (self.getName(), ) 

    def shutdown(self):
        self._shutdown = True

    def run_thread(self, *arg, **kw):
        pass

class Connection(Thread):
    class Dispatch(Thread): pass
        
    def run_thread(self):
        for value in self.read():
            if debug_dispatch: print "%s: DISPATCH: %s" % (self.getName(), value) 
            self.dispatch(value)
            if debug_dispatch: print "%s: DISPATCH DONE: %s" % (self.getName(), value) 

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
                return
            if status:
                socket, address = self.subject.accept()
                yield socket.makefile('r+')

class ThreadedClient(Thread):
    Dispatch = ClientConnection

    def run_thread(self):
        self.dispatch(self.subject)

class EchoClient(ClientConnection):
    def dispatch(self, value):
        json.json(value, self.subject)
        self.subject.flush()

class EchoServer(ServerConnection):
    Dispatch = EchoClient

class ThreadedEchoServer(ServerConnection):
    class Dispatch(ThreadedClient):
        Dispatch = EchoClient

class TestConnection(unittest.TestCase):
    def test_client(self):
        sockets = [s.makefile('r+') for s in socket.socketpair()]
        reader = json.ParserReader(sockets[0])
        echo_server = EchoClient(sockets[1])

        obj = {'foo':1, 'bar':[1, 2]}
        json.json(obj, sockets[0])
        return_obj = reader.read_value()
        
        self.assertEqual(obj, return_obj)

    def test_server(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind(('', 4712))
        server_socket.listen(1)
        echo_server = EchoServer(server_socket, name="EchoServer")

        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect(('localhost', 4712))
        client_socket = client_socket.makefile('r+')

        obj = {'foo':1, 'bar':[1, 2]}
        json.json(obj, client_socket)
        client_socket.flush()

        reader = json.ParserReader(client_socket)
        return_obj = reader.read_value()
        
        self.assertEqual(obj, return_obj)
        echo_server.shutdown()
        time.sleep(1)

    def test_threaded_server(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind(('', 4712))
        server_socket.listen(1)
        echo_server = ThreadedEchoServer(server_socket, name="EchoServer")

        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect(('localhost', 4712))
        client_socket = client_socket.makefile('r+')

        obj = {'foo':1, 'bar':[1, 2]}
        json.json(obj, client_socket)
        client_socket.flush()

        reader = json.ParserReader(client_socket)
        return_obj = reader.read_value()
        
        self.assertEqual(obj, return_obj)
        echo_server.shutdown()

if __name__ == "__main__":
    unittest.main()
