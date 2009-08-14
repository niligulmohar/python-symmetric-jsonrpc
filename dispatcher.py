import json, threading, unittest, socket

debug_dispatch = False

class Connection(threading.Thread):
    def __init__(self, conn, *arg, **kw):
        self.conn = conn
        threading.Thread.__init__(self, *arg, **kw)
        self.start()
          
    def run(self):
        if debug_dispatch: print "%s: RUN" % (self.getName(), ) 
        for value in self.read():
            if debug_dispatch: print "%s: DISPATCH: %s" % (self.getName(), value) 
            self.dispatch(value)
    
    def read(self):
        pass

    def dispatch(self, value):
        pass
    
class ClientConnection(Connection):
    def __init__(self, conn, *arg, **kw):
        self.reader = json.ParserReader(conn)
        Connection.__init__(self, conn, *arg, **kw)
    
    def read(self):
        return self.reader.read_values()

    def dispatch(self, value):
        pass

class ServerConnection(Connection):
    ClientConnection = ClientConnection

    def read(self):
        try:
            while True:
                yield self.conn.accept()
        except Exception,e:
            print "NANANAN", self.conn, e
            pass
    
    def dispatch(self, (socket, address)):
        self.server_dispatch(self.ClientConnection(socket.makefile('r+'), name="%s/%s" % (self.getName(), self.ClientConnection.__name__)))

    def server_dispatch(self, conn):
        pass

class ThreadDispatcherMixin(object):
    def dispatch(self, *arg, **kw):
        thread = self.DispatchThread(self, *arg, **kw)
        thread.start()

    class DispatchThread(threading.Thread):
        def __init__(self, conn, *arg, **kw):
            self.conn = conn
            threading.Thread.__init__(self, args=arg, kwargs=kw)
            
        def run(self, *arg, **kw):
            return self.conn.dispatch_in_thread(*arg, **kw)

    def dispatch_in_thread(self, *arg, **kw):
        pass

class EchoClient(ClientConnection):
    def dispatch(self, value):
        json.json(value, self.conn)
        self.conn.flush()

class EchoServer(ServerConnection):
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
        server_socket.bind(('', 4711))
        server_socket.listen(1)
        echo_server = EchoServer(server_socket, name="EchoServer")

        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect(('localhost', 4711))
        client_socket = client_socket.makefile('r+')

        obj = {'foo':1, 'bar':[1, 2]}
        json.json(obj, client_socket)
        client_socket.flush()

        reader = json.ParserReader(client_socket)
        return_obj = reader.read_value()
        
        self.assertEqual(obj, return_obj)

if __name__ == "__main__":
    unittest.main()
