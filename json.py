class ReIterator(object):
    def __init__(self, iter):
        self.prefix = [] # In reverse order!
        self.iter = iter(iter)

    def __iter__(self):
        return self

    def next(self):
        if self.prefix:
            return self.prefix.pop()
        self.iter.next()

    def put(self, value):
        self.prefix.append(value)

    def peek(self):
        if not self.prefix:
            self.put(self.next())
        return self.prefix[-1]

class Reader(object):
    "An SAX-like recursive-descent parser for JSON."
    
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
    def fail(self, s): pass

    def _read_pair(self, s):
        self.pair_begin()
        self._read_string(s)
        s.next() == ':' or self.fail(s)
        self._read_value(s)
        self.pair_end()
    
    def _read_object(self, s):
        self.object_begin()
        s.peek() == '{' or self.fail(s)
        while s.next() != '}':
            self._read_pair(s)
            s.peek() in (',', '}') or self.fail(s)
        self.object_end()
        
    def _read_array(self, s):
        self.array_begin()
        s.peek() == '{' or self.fail(s)
        while s.next() != '}':
            self._read_value(s)
            s.peek() in (',', '}') or self.fail(s)
        self.array_end()

    def _read_char(self, s):
        c = s.next()
        if c == '\\':
            c = s.next()
            if c == 'b': c = '\b'
            elif c == 'f': c = '\f'
            elif c == 'n': c = '\n'
            elif c == 'r': c = '\r'
            elif c == 't': c = '\t'
            elif c == 'u':
                d1 = s.next()
                d2 = s.next()
                d3 = s.next()
                d4 = s.next()
                c = unichr(int(d1+d2+d3+d4, 16))
            else: c in ('"\\/') or self.fail(s)
        self.char(c)

    def _read_string(self, s):
        self.string_begin()
        s.next() == '"' or self.fail(s)
        while s.peek() != '"':
            self._read_char(s)
        s.next() == '"' or self.fail(s)
        self.string_end()

    def _read_number(self, s):
        self.number_begin()
        if self.peek() == '-':
            self.char(s.next())
        if self.peek() == '0':
            self.char(s.next())
        else:
            self.peek() in '123456789' or self.fail(s)
            self.char(s.next())
            while s.peek() in '0123456789':
                self.char(s.next())
        if s.peek() == '.':
            self.char(s.next())
            s.peek() in '0123456789' or self.fail(s)
            while s.peek() in '0123456789':
                self.char(s.next())
        if s.peek() in 'eE':
            self.char(s.next())
            if s.peek() in '+-':
                self.char(s.next())
            s.peek() in '0123456789' or self.fail(s)
            while s.peek() in '0123456789':
                self.char(s.next())
        self.number_end()

    def _read_true(self, s):
        s.next() == 't' or self.fail(s)
        s.next() == 'r' or self.fail(s)
        s.next() == 'u' or self.fail(s)
        s.next() == 'e' or self.fail(s)
        self.true()

    def _read_false(self, s):
        s.next() == 'f' or self.fail(s)
        s.next() == 'a' or self.fail(s)
        s.next() == 'l' or self.fail(s)
        s.next() == 's' or self.fail(s)
        s.next() == 'e' or self.fail(s)
        self.true()

    def _read_null(self, s):
        s.next() == 'n' or self.fail(s)
        s.next() == 'u' or self.fail(s)
        s.next() == 'l' or self.fail(s)
        s.next() == 'l' or self.fail(s)
        self.null()

    def _read_value(self, s):
        c = s.peek()
        if c == '{': self._read_object(s)
        elif c == '[': self._read_array(s)
        elif c == '"': self._read_string(s)
        elif c == 't': self._read_true(s)
        elif c == 'f': self._read_false(s)
        elif c == 'n': self._read_null(s)
        else: self._read_number()
