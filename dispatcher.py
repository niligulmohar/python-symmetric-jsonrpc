import json, threading


class Connection(object):
    def __init__(self, socket):
        self.socket = socket
        self.dispatcher_thread = self.DispatcherThread(self)
        self.dispatcher_thread.start()
        
    class DispatcherThread(Threading.Thread):
        def __init__(self, conn, *arg, **kw):
            self.conn = conn
            self.reader = json.ParserReader(self.conn.socket)
            threading.Thread.__init__(self, *arg, **kw)
          
        def run(self):
            for value in self.reader.read_values():
                self.conn.dispatch(value)

    def dispatch(self, value):
        pass

class ServerConnection(object):
    ClientConnection = Connection

    def __init__(self, socket):
        self.socket = socket
        self.dispatcher_thread = self.DispatcherThread(self)
        self.dispatcher_thread.start()

    class DispatcherThread(Threading.Thread):
        def __init__(self, conn, *arg, **kw):
            self.conn = conn
            threading.Thread.__init__(self, *arg, **kw)

        def run(self):
            while True:
                socket, address = self.conn.socket.accept()
                self.dispatch_snd(socket, address)

        def dispatch(self, socket, address):
            self.conn.dispatch(self.ClientConnection(socket))

    def dispatch(self, conn):
        pass

class ThreadDispatcherMixin(object):
    def dispatch(self, *arg, **kw):
        thread = self.DispatchedThread(self, *arg, **kw)
        thread.start()

    class DispatchedThread(threading.Thread):
        def __init__(self, conn, *arg, **kw):
            self.conn = conn
            threading.Thread.__init__(self, args=arg, kwargs=kw)
            
        def run(self, *arg, **kw):
            pass
