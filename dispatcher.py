import json, threading, unittest, socket, time, select

debug_dispatch = True

class Connection(threading.Thread):
    def __init__(self, conn, *arg, **kw):
        self.conn = conn
        self._shutdown = False
        threading.Thread.__init__(self, *arg, **kw)
        self.start()
          
    def run(self):
        if debug_dispatch: print "%s: RUN" % (self.getName(), ) 
        for value in self.read():
            if debug_dispatch: print "%s: DISPATCH: %s" % (self.getName(), value) 
            self.dispatch(value)
            if debug_dispatch: print "%s: DISPATCH DONE: %s" % (self.getName(), value) 
        if debug_dispatch: print "%s: END" % (self.getName(), ) 

    def shutdown(self):
        self._shutdown = True

    def read(self):
        pass

    def dispatch(self, value):
        pass
    
class ClientConnection(Connection):
    def __init__(self, conn, *arg, **kw):
        self.reader = json.ParserReader(conn)
        Connection.__init__(self, conn, *arg, **kw)
    
    def read(self):
        # FIXME: How to handle shutdown here?
        return self.reader.read_values()

    def dispatch(self, value):
        pass

class ServerConnection(Connection):
    ClientConnection = ClientConnection

    def read(self):
        poll = select.poll()
        poll.register(self.conn, select.POLLIN)

        while True:
            status = poll.poll(100)
            if self._shutdown:
                return
            if status:
                yield self.conn.accept()
        
    def dispatch(self, (socket, address)):
        self.ClientConnection(socket.makefile('r+'), name="%s/%s" % (self.getName(), self.ClientConnection.__name__))

class ThreadedClient(threading.Thread):
    ClientConnection = ClientConnection

    def __init__(self, conn, *arg, **kw):
        self.conn = conn
        threading.Thread.__init__(self, *arg, **kw)
        self.start()

    def run(self):
        if debug_dispatch: print "%s: RUN" % (self.getName(), ) 
        self.dispatch()
        if debug_dispatch: print "%s: END" % (self.getName(), ) 

    def dispatch(self):
        self.ClientConnection(self.conn, name="%s/%s" % (self.getName(), self.ClientConnection.__name__))

class EchoClient(ClientConnection):
    def dispatch(self, value):
        json.json(value, self.conn)
        self.conn.flush()

class EchoServer(ServerConnection):
    ClientConnection = EchoClient

class ThreadedEchoServer(ServerConnection):
    class ClientConnection(ThreadedClient):
        ClientConnection = EchoClient

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
