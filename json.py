class ReIterator(object):
    def __init__(self, i):
        self.prefix = [] # In reverse order!
        self.i = iter(i)

    def __iter__(self):
        return self

    def next(self):
        if self.prefix:
            return self.prefix.pop()
        return self.i.next()

    def put(self, value):
        self.prefix.append(value)

    def peek(self):
        if not self.prefix:
            self.put(self.i.next())
        return self.prefix[-1]

class Reader(object):
    "An SAX-like recursive-descent parser for JSON."

    def __init__(self, s):
        self.s = ReIterator(s)
    
    # Override these in a subclass to actually do something with the
    # parsed data
    def pair_begin(self): pass
    def pair_end(self): pass
    def object_begin(self): pass
    def object_end(self): pass
    def array_begin(self): pass
    def array_end(self): pass
    def string_begin(self): pass
    def string_end(self): pass
    def number_begin(self): pass
    def number_end(self): pass
    def char(self, c): pass 
    def true(self): pass
    def false(self): pass
    def null(self): pass
    def fail(self, msg): pass

    def _assert(self, c, values):
        if c not in values:
            self.fail("<%s> not in <%s>" % (c, values))
        return c

    def _read_pair(self):
        self.pair_begin()
        self._read_string()
        self._assert(self.s.next(), ':')
        self._read_value()
        self.pair_end()
    
    def _read_object(self):
        self.object_begin()
        self._assert(self.s.peek(), '{')
        while self.s.next() != '}':
            self._read_pair()
            self._assert(self.s.peek(), ',}')
        self.object_end()
        
    def _read_array(self):
        self.array_begin()
        self._assert(self.s.peek(), '{')
        while self.s.next() != '}':
            self._read_value()
            self._assert(self.s.peek(), ',}')
        self.array_end()

    def _read_char(self):
        c = self.s.next()
        if c == '\\':
            c = self.s.next()
            if c == 'b': c = '\b'
            elif c == 'f': c = '\f'
            elif c == 'n': c = '\n'
            elif c == 'r': c = '\r'
            elif c == 't': c = '\t'
            elif c == 'u':
                d1 = self.s.next()
                d2 = self.s.next()
                d3 = self.s.next()
                d4 = self.s.next()
                c = unichr(int(d1+d2+d3+d4, 16))
            else: self._assert(c, '"\\/')
        self.char(c)

    def _read_string(self):
        self.string_begin()
        self._assert(self.s.next(), '"')
        while self.s.peek() != '"':
            self._read_char()
        self._assert(self.s.next(), '"')
        self.string_end()

    def _read_number(self):
        self.number_begin()
        if self.s.peek() == '-':
            self.char(self.s.next())
        if self.s.peek() == '0':
            self.char(self.s.next())
        else:
            self._assert(self.s.peek(), '123456789')
            self.char(self.s.next())
            while self.s.peek() in '0123456789':
                self.char(self.s.next())
        if self.s.peek() == '.':
            self.char(self.s.next())
            self._assert(self.s.peek(), '0123456789')
            while self.s.peek() in '0123456789':
                self.char(self.s.next())
        if self.s.peek() in 'eE':
            self.char(self.s.next())
            if self.s.peek() in '+-':
                self.char(self.s.next())
            self._assert(self.s.peek(), '0123456789')
            while self.s.peek() in '0123456789':
                self.char(self.s.next())
        self.number_end()

    def _read_true(self):
        self._assert(self.s.next(), 't')
        self._assert(self.s.next(), 'r')
        self._assert(self.s.next(), 'u')
        self._assert(self.s.next(), 'e')
        self.true()

    def _read_false(self):
        self._assert(self.s.next(), 'f')
        self._assert(self.s.next(), 'a')
        self._assert(self.s.next(), 'l')
        self._assert(self.s.next(), 's')
        self._assert(self.s.next(), 'e')
        self.true()

    def _read_null(self):
        self._assert(self.s.next(), 'n')
        self._assert(self.s.next(), 'u')
        self._assert(self.s.next(), 'l')
        self._assert(self.s.next(), 'l')
        self.null()

    def _read_value(self):
        c = self.s.peek()
        if c == '{': return self._read_object()
        elif c == '[': return self._read_array()
        elif c == '"': return self._read_string()
        elif c == 't': return self._read_true()
        elif c == 'f': return self._read_false()
        elif c == 'n': return self._read_null()
        else: return self._read_number()

    def read_value(self):
        return self._read_value()

    def read_values(self):
        while True:
            self._read_value()    

class DebugReader(Reader):
    def pair_begin(self): print '('
    def pair_end(self): print ')'
    def object_begin(self): print '{'
    def object_end(self): print '}'
    def array_begin(self): print '['
    def array_end(self): print ']'
    def string_begin(self): print '"'
    def string_end(self): print '"'
    def number_begin(self): print '<'
    def number_end(self): print '>'
    def char(self, c): print repr(c)
    def true(self): print "TRUE"
    def false(self): print "FALSE"
    def null(self): print "NULL"
    def fail(self, msg): raise Exception(msg)

try:
    DebugReader('{"foo":4}').read_value()
except:
    import sys, pdb
    sys.last_traceback = sys.exc_info()[2]
    pdb.pm()
    
