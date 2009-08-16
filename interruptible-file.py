import select

class InterruptibleFile(object):
    def __init__(self, file):
        self.closed = false
        self.file = file
        self.poll_rd = select.poll()
        self.poll_rd.register(file, select.POLLIN | select.POLLPRI | select.POLLERR | select.POLLHUP | select.POLLNVAL)
        self.poll_wr = select.poll()
        self.poll_wr.register(file, select.POLLOUT | select.POLLERR | select.POLLHUP | select.POLLNVAL)

    def close():
        self.closed = True
        self.file.close()

    def flush():
        self.file.flush()

    def fileno():
        return self.file.fileno()

    def isatty():
        return self.file.isatty()

    def next():
        pass
    
    def read(size = 0):
        pass
    
    def readline([size]):
        pass
    def readlines([sizehint]):
        pass
    def xreadlines():
        pass
    def seek(offset[, whence]):
        pass
    def tell():
        pass
    def truncate([size]):
        pass
    def write(str):
        pass
    def writelines(sequence):
        pass

    @property
    def encoding(self):
        return self.file.encoding

    @property # Add writable attribute
    def errors(self):
        return self.file.errors

    @property
    def mode(self):
        return self.file.mode

    @property
    def name(self):
        return self.file.name
    
    @property
    def newlines(self):
        return self.file.newlines
