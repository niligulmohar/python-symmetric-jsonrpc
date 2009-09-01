import select

class WriterWrapper(object):
    poll_timeout = 1000

    def __new__(cls, f):
        if cls is not WriterWrapper:
            return object.__new__(cls)
        elif hasattr(f, "write"):
            return FileWriter(f)
        elif hasattr(f, "send"):
            return SocketWriter(f)
        else:
            return f
            
    def __init__(self, f):
        self.f = f
        self.poll = select.poll()
        self.poll.register(f, select.POLLOUT | select.POLLERR | select.POLLHUP | select.POLLNVAL)
        self.closed = False

    def close(self):
        self.closed = True
        self.f.close()

    def write(self, s):
        self._wait()
        self._write(s)

    def _wait(self):
        res = []
        while not res and not self.closed:
            res = self.poll.poll(self.poll_timeout)
        if self.closed:
            raise EOFError
    
    def _write(self, s):
        raise NotImplementedError

class FileWriter(WriterWrapper):
    def _write(self, s):
        self.f.write(s)

class SocketWriter(WriterWrapper):
    def _write(self, s):
        self.f.send(s)

class ReaderWrapper(object):
    poll_timeout = 1000
    
    def __new__(cls, f):
        if cls is not ReaderWrapper:
            return object.__new__(cls)
        elif hasattr(f, "read"):
            return FileReader(f)
        elif hasattr(f, "recv"):
            return SocketReader(f)
        else:
            return f

    def __init__(self, file):
        self.file = file
        self.poll = select.poll()
        self.poll.register(file, select.POLLIN | select.POLLPRI | select.POLLERR | select.POLLHUP | select.POLLNVAL)
        self.closed = False

    def __iter__(self):
        return self

    def next(self):
        try:
            self._wait()
        except EOFError:
            raise StopIteration
        result = self._read()
        if result == '':
            raise StopIteration
        else:
            return result

    def close(self):
        self.closed = True
        self.file.close()

    def _wait(self):
        res = []
        while not res and not self.closed:
            res = self.poll.poll(self.poll_timeout)
        if self.closed:
            raise EOFError

    def _read(self):
        raise NotImplementedError

class FileReader(ReaderWrapper):  
    def _read(self):
        return self.file.read(1)

class SocketReader(ReaderWrapper):  
    def _read(self):
        return self.file.recv(1)

class ReIterator(object):
    def __init__(self, i):
        self.prefix = [] # In reverse order!
        self.closable = i
        self.i = iter(i)

    def __iter__(self):
        return self

    def close(self):
        self.closable.close()

    def next(self):
        if self.prefix:
            return self.prefix.pop()
        return self.i.next()

    def put(self, value):
        self.prefix.append(value)

    def peek(self):
        try:
            if not self.prefix:
                self.put(self.i.next())
            return self.prefix[-1]
        except StopIteration:
            raise EOFError()
