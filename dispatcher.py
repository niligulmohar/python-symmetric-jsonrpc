import threading, select

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

class ServerConnection(Connection):
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
    def _init(self, *arg, **kw):
        Thread._init(self, *arg, **kw)
        self.dispatch_subject = self.subject
        self.subject = self.parent.subject

    def run_thread(self):
        self.dispatch(self.dispatch_subject)

    def dispatch(self, subject):
        self.Dispatch(parent = self, subject = subject)
