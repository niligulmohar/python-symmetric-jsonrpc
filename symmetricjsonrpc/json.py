#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim: set fileencoding=UTF-8 :

# python-symmetric-jsonrpc
# Copyright (C) 2009 Egil Moeller <redhog@redhog.org>
# Copyright (C) 2009 Nicklas Lindgren <nili@gulmohar.se>

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# Lesser General Public License for more details.

# You should have received a copy of the GNU Lesser General Public
# License along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
# USA

"""JSON (de)serialization facilities."""

import sys
import StringIO
import unittest

import wrappers

def from_json(str):
    """Return a python object representing the json value in str."""
    r = Reader(str)
    return r.read_value()

def to_json(obj):
    """Return a json string representing the python object obj."""
    i = StringIO.StringIO()
    w = Writer(i, encoding='UTF-8')
    w.write_value(obj)
    return i.getvalue()

class Writer(object):
    """A serializer for python values to JSON. Allowed types for
    values to serialize are:

        * None
        * True
        * False
        * Integer
        * Float
        * String
        * Unicode
        * List
        * Dict (keys must be String or Unicode)
        * any object with a __to_json__ method

    The writer must be instantiated with a file-like object to write
    the serialized json to as sole argument. To actually serialize
    data, call the write_value() or write_values() methods."""

    def __init__(self, s, encoding=None):
        self.encoding = encoding
        self.s = wrappers.WriterWrapper(s)

    def close(self):
        self.s.close()

    def write_value(self, value):
        self.unflushed_write_value(value)
        self.s.flush()

    def unflushed_write_value(self, value):
        if hasattr(value, '__to_json__'):
            self.unflushed_write_value(value.__to_json__())
        elif isinstance(value, unicode):
            self.s.write('"')
            for c in value:
                if c == '\b':
                    self.s.write(r'\b')
                elif c == '\t':
                    self.s.write(r'\t')
                elif c == '\n':
                    self.s.write(r'\n')
                elif c == '\f':
                    self.s.write(r'\f')
                elif c == '\r':
                    self.s.write(r'\r')
                elif c == '"':
                    self.s.write(r'\"')
                elif c == '\\':
                    self.s.write(r'\\')
                elif c >= ' ' and c <= '~':
                    self.s.write(c.encode('ascii'))
                elif c > '~':
                    self.s.write(r'\u%04x' % ord(c))
                else:
                    raise Exception("Cannot encode character %x into json string" % ord(c))
            self.s.write('"')
        elif isinstance(value, str):
            self.unflushed_write_value(value.decode(self.encoding or sys.getdefaultencoding()))
        elif isinstance(value, bool):
            self.s.write(value and 'true' or 'false')
        elif isinstance(value, int) or isinstance(value, float) or isinstance(value, long):
            r = repr(value)
            if r[-1] == 'L':
                r = r[:-1]
            self.s.write(r)
        elif value == None:
            self.s.write('null')
        elif hasattr(value, '__iter__'):
            if hasattr(value,'iteritems'):
                self.s.write('{')
                for n, (k, v) in enumerate(value.iteritems()):
                    if (n > 0):
                        self.s.write(',')
                    self.unflushed_write_value(k)
                    self.s.write(':')
                    self.unflushed_write_value(v)
                self.s.write('}')
            else:
                self.s.write('[')
                for n, i in enumerate(value):
                    if (n > 0):
                        self.s.write(',')
                    self.unflushed_write_value(i)
                self.s.write(']')
        else:
            raise Exception("Cannot encode %s of type %s to json" % (value,type(value)))

    def unflushed_write_values(self, values):
        for value in values:
            self.unflushed_write_value(value)

class Tokenizer(object):
    """A SAX-like recursive-descent parser for JSON.

    This class does not actually parse JSON into Python objects, it
    only provides tokenization (just like a SAX parser for XML).

    This class must be subclassed to be useful. See Reader for
    a full example."""

    def __init__(self, s):
        self.closable = wrappers.ReaderWrapper(s)
        self.s = wrappers.ReIterator(self.closable)

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
            self.fail("%s not in %s" % (repr(c), repr(values)))
        return c

    def _read_space(self):
        while self.s.peek() in ' \t\r\n':
            self.s.next()

    def _read_pair(self):
        self.pair_begin()
        self._read_string()
        self._read_space()
        self._assert(self.s.next(), ':')
        self._read_space()
        self._read_value()
        self.pair_end()

    def _read_object(self):
        self.object_begin()
        self._assert(self.s.next(), '{')
        self._read_space()
        if self.s.peek() != '}':
            while True:
                self._read_pair()
                self._read_space()
                if self.s.peek() == '}':
                    break
                self._assert(self.s.next(), ',')
                self._read_space()
        self._assert(self.s.next(), '}')
        self.object_end()

    def _read_array(self):
        self.array_begin()
        self._assert(self.s.next(), '[')
        self._read_space()
        if self.s.peek() != ']':
            while True:
                self._read_value()
                self._read_space()
                if self.s.peek() == ']':
                    break
                self._assert(self.s.next(), ',')
                self._read_space()
        self._assert(self.s.next(), ']')
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
        # Note: We catch this here, as numbers don't have any special
        # ending character. If we end up with an EOF and ignore it
        # here, while the number is part of a bigger structure, the
        # parsing function for the surrounding structure will do
        # next/peek again and it will be re-raised.
        try:
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
        except EOFError:
            pass
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
        self.false()

    def _read_null(self):
        self._assert(self.s.next(), 'n')
        self._assert(self.s.next(), 'u')
        self._assert(self.s.next(), 'l')
        self._assert(self.s.next(), 'l')
        self.null()

    def _read_value(self):
        self._read_space()
        c = self.s.peek()
        if c == '{': return self._read_object()
        elif c == '[': return self._read_array()
        elif c == '"': return self._read_string()
        elif c == 't': return self._read_true()
        elif c == 'f': return self._read_false()
        elif c == 'n': return self._read_null()
        else: return self._read_number()

    def close(self):
        self.closable.close()

    def read_value(self):
        return self._read_value()

    def read_values(self):
        while True:
            self._read_value()

class Reader(Tokenizer):
    """A JSON parser that parses JSON strings read from a file-like
    object or character iterator (for example a string) into Python
    values.

    The parser must be instantiated with the file-like object or
    string as its sole argument. To actually parse any values, call
    either the read_value() method, or iterate over the return value
    of the read_values() method."""

    def __init__(self, s, object_initializer = None):
        Tokenizer.__init__(self, s)
        self.object_initializer = object_initializer
    def _struct_begin(self):
        self.state.append([])
    def _struct_end(self):
        self.state[-2].append(self.state[-1])
        del self.state[-1]
    def pair_begin(self): self._struct_begin()
    def pair_end(self): self._struct_end()
    def object_begin(self): self._struct_begin()
    def object_end(self):
        self.state[-1] = dict(self.state[-1])
        if '__jsonclass__' in self.state[-1]:
            self.class_object()
        self._struct_end()
    def class_object(self):
        if self.object_initializer and self.state[-1]['__jsonclass__'][0] in self.object_initializer:
            cls = self.state[-1].pop('__jsonclass__')
            params = cls[1:]
            cls = self.object_initializer[cls[0]]
            self.state[-1] = cls(params, self.state[-1])
    def array_begin(self): self._struct_begin()
    def array_end(self): self._struct_end()
    def string_begin(self): self.state.append(u"")
    def string_end(self):  self._struct_end()
    def number_begin(self): self.state.append(u"")
    def number_end(self):
        if '.' in self.state[-1] or 'e' in self.state[-1] or 'E' in self.state[-1]:
            self.state[-1] = float(self.state[-1])
        else:
            self.state[-1] = int(self.state[-1])
        self._struct_end()
    def char(self, c): self.state[-1] = self.state[-1] + c
    def true(self): self.state[-1].append(True)
    def false(self): self.state[-1].append(False)
    def null(self): self.state[-1].append(None)
    def fail(self, msg): raise Exception(msg)
    def read_value(self):
        self.state = [[]]
        self._read_value()
        return self.state[-1][-1]
    def read_values(self):
        try:
            while True:
                self.state = [[]]
                self._read_value()
                yield self.state[-1][-1]
        except EOFError:
            return

class DebugTokenizer(object):
    def pair_begin(self): print '('; print self.state; return super(DebugTokenizer, self).pair_begin()
    def pair_end(self): print ')'; print self.state; return super(DebugTokenizer, self).pair_end()
    def object_begin(self): print '{'; print self.state; return super(DebugTokenizer, self).object_begin()
    def object_end(self): print '}'; print self.state; return super(DebugTokenizer, self).object_end()
    def array_begin(self): print '['; print self.state; return super(DebugTokenizer, self).array_begin()
    def array_end(self): print ']'; print self.state; return super(DebugTokenizer, self).array_end()
    def string_begin(self): print '"'; print self.state; return super(DebugTokenizer, self).string_begin()
    def string_end(self): print '"'; print self.state; return super(DebugTokenizer, self).string_end()
    def number_begin(self): print '<'; print self.state; return super(DebugTokenizer, self).number_begin()
    def number_end(self): print '>'; print self.state; return super(DebugTokenizer, self).number_end()
    def char(self, c): print repr(c); print self.state; return super(DebugTokenizer, self).char(c)
    def true(self): print "TRUE"; print self.state; return super(DebugTokenizer, self).true()
    def false(self): print "FALSE"; print self.state; return super(DebugTokenizer, self).false()
    def null(self): print "NULL"; print self.state; return super(DebugTokenizer, self).null()
    def fail(self, msg): super(DebugTokenizer, self).fail(); raise Exception(msg)

class DebugReader(DebugTokenizer, Reader): pass

#### Test code ####

class TestJson(unittest.TestCase):
    import socket
    import tempfile
    import threading

    def assertReadEqual(self, str, obj):
        reader = Reader(str)
        read_obj = reader.read_value()
        self.assertEqual(obj, read_obj)
        io = self.tempfile.TemporaryFile()
        Writer(io).write_value(obj)
        io.seek(0)
        reader1 = Reader(io)
        read_obj1 = reader1.read_value()
        self.assertEqual(obj, read_obj1)
    def assertWriteEqual(self, str, obj):
        self.assertEqual(str, to_json(obj))
    def test_to_json(self):
        STR = '["string",false,null]'
        OBJ = [u"string", False, None]
        self.assertEqual(to_json(OBJ), STR)
    def test_from_json(self):
        STR = '{"array": ["string",false,null],"object":{"number":4711,"bool":true}}'
        OBJ = {u"array": [u"string", False, None], u"object": {u"number": 4711, u"bool": True}}
        self.assertEqual(from_json(STR), OBJ)
    def test_single_number_from_json(self):
        STR = '3.33'
        OBJ = 3.33
        self.assertEqual(from_json(STR), OBJ)
    def test_read_value(self):
        STR = '{"array": ["string",false,null],"object":{"number":4711,"bool":true}}'
        OBJ = {u"array": [u"string", False, None], u"object": {u"number": 4711, u"bool": True}}
        self.assertReadEqual(STR, OBJ)
    def test_read_numbers(self):
        STR = '[0, -1, 0.2, 1e+4, -2.5E-5, 1e20]'
        self.assertReadEqual(STR, eval(STR))
    def test_read_escape_string(self):
        STR = r'"\b\f\n\r\t\u1234"'
        OBJ = u"\b\f\n\r\t\u1234"
        self.assertReadEqual(STR, OBJ)
    def test_read_quote_string(self):
        STR = r'"\""'
        OBJ = u"\""
        self.assertReadEqual(STR, OBJ)
    def test_read_solidus_string(self):
        STR = r'"\/"'
        OBJ = u"/"
        self.assertReadEqual(STR, OBJ)
    def test_read_reverse_solidus_string(self):
        STR = r'"\\"'
        OBJ = u"\\"
        self.assertReadEqual(STR, OBJ)
    def test_read_whitespace(self):
        STR = ''' {
"array" : [ ] ,
"object" : { }
} '''
        self.assertReadEqual(STR, eval(STR))
    def test_read_values(self):
        STR = "{}[]true false null"
        reader = Reader(STR)
        values = [{}, [], True, False, None]

        for i, r in enumerate(reader.read_values()):
            self.assertEqual(r, values[i])
    def test_encode_invalid_control_character(self):
        self.assertRaises(Exception, lambda: json('\x00', self.tempfile.TemporaryFile()))
    def test_encode_invalid_object(self):
        self.assertRaises(Exception, lambda: json(Tokenizer(""), self.tempfile.TemporaryFile()))
    def test_read_object(self):
        STR = '{"__jsonclass__":["foo","bar"],"naja":123}'
        def foo(arg, kw):
            assert arg == ["bar"]
            assert kw == {"naja":123}
            return True
        reader = Reader(STR, {'foo': foo})
        assert reader.read_value() is True
    def test_broken_socket(self):
        sockets = self.socket.socketpair()
        reader = Reader(sockets[0])
        sockets[0].close()
        self.assertRaises(self.socket.error, lambda: reader.read_value())

    def test_eof(self):
        import cStringIO

        obj = {'foo':1, 'bar':[1, 2]}
        io0 = self.tempfile.TemporaryFile()
        Writer(io0).write_value(obj)
        io0.seek(0)
        full_json_string = io0.read()

        for json_string, eof_error in ((full_json_string, False), (full_json_string[0:10], True), ('', True)):
            io1 = self.tempfile.TemporaryFile()
            io1.write(json_string)
            io1.seek(0)
            reader = Reader(io1)
            if eof_error:
                self.assertRaises(EOFError, lambda: reader.read_value())
            else:
                self.assertEqual(obj, reader.read_value())


    def test_closed_socket(self):
        class Timeout(self.threading.Thread):
            def run(self1):
                obj = {'foo':1, 'bar':[1, 2]}
                io = self.tempfile.TemporaryFile()
                Writer(io).write_value(obj)
                io.seek(0)
                full_json_string = io.read()

                for json_string, eof_error in ((full_json_string, False), (full_json_string[0:10], True), ('', True)):
                    sockets = self.socket.socketpair()
                    reader = Reader(sockets[0])

                    for c in json_string:
                        while not sockets[1].send(c): pass
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

    def test_write_object(self):
        class SomeObj(object):
            def __init__(self, x):
                self.x = x

            def __to_json__(self):
                return {'__jsonclass__': ['SomeObj'], 'x': self.x}

        self.assertWriteEqual('{"x":4711,"__jsonclass__":["SomeObj"]}', SomeObj(4711))

if __name__ == "__main__":
    unittest.main()
