#! /bin/env python
# -*- coding: UTF-8 -*-
# vim: set fileencoding=UTF-8 :

# python-symmetric-jsonrcp
# Copyright (C) 2009 Egil Moeller <redhog@redhog.org>
# Copyright (C) 2009 Nicklas Lindgren <nili@gulmohar.se>

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

from __future__ import with_statement

import threading, select

class Thread(threading.Thread):

    """This class is the base class for a set of threading.Thread
    subclasses that provides automatic start, some debugging print-out
    for start/stop, a subject resource to manage (like a socket), and
    possibly a child/parent relationship with another thread."""

    debug_thread = False

    def __init__(self, *arg, **kw):
        self._init(*arg, **kw)
        self.start()
        self.run_parent()

    def _init(self, subject, parent = None, *arg, **kw):
        self.children = []
        self.subject = subject
        self.parent = parent
        if hasattr(self.parent, "children"):
            self.parent.children.append(self)
        self._shutdown = False
        if 'name' not in kw:
            if self.parent:
                kw['name'] = "%s/%s" % (self.parent.getName(), type(self).__name__)
            else:
                kw['name'] = type(self).__name__
        threading.Thread.__init__(self, *arg, **kw)

    def _exit(self):
        for child in list(self.children):
            child.join()
        if hasattr(self.parent, "children"):
            self.parent.children.remove(self)

    def run(self, *arg, **kw):
        if self.debug_thread: print "%s: BEGIN" % self.getName()
        self.run_thread(*arg, **kw)
        if self.debug_thread: print "%s: TEARDOWN: %s" % (self.getName(), ', '.join(child.getName() for child in self.children))
        self._exit()
        if self.debug_thread: print "%s: END" % self.getName()

    def shutdown(self):
        """Do not call this from within a a child thread or you will deadlock. Use the ShutDownThread helper for that instead."""
        if self.debug_thread: print "%s: shutdown: %s" % (threading.currentThread().getName(), self.getName(),)
        for child in list(self.children):
            child.shutdown()
        self._shutdown = True
        try:
            self.join()
        except RuntimeError:
            # Whatever, if this is the current thread, just ignore it...
            pass
        if self.debug_thread: print "%s: shutdown done: %s" % (threading.currentThread().getName(), self.getName(),)

    def run_parent(self):
        pass

    def run_thread(self, *arg, **kw):
        pass

class ShutDownThread(Thread):
    def run_thread(self):
        self.subject.shutdown()

class Connection(Thread):
    """A connection manager thread base class."""

    debug_dispatch = False

    _dispatcher_class = "Request"

    def run_thread(self):
        for value in self.read():
            if self.debug_dispatch: print "%s: DISPATCH: %s" % (self.getName(), value)
            self.dispatch(value)
            if self.debug_dispatch: print "%s: DISPATCH DONE: %s" % (self.getName(), value)

    def read(self):
        pass

    def dispatch(self, subject):
        getattr(self, self._dispatcher_class)(parent = self, subject = subject)

class ServerConnection(Connection):
    """Connection manager thread handling a listening socket,
    dispatching inbound connections."""

    _dispatcher_class = "InboundConnection"

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
                yield socket

class ThreadedClient(Thread):
    """A dispatch manager that can be used to wrap some other dispatch
    manager to have it started and entierly run inside an extra
    thread. This is actually useful to wrap connection managers with
    too, to have their run_parent() run inside a separate thread
    too. See the RPC module for a good example of this."""

    _dispatcher_class = "Thread"

    def _init(self, *arg, **kw):
        Thread._init(self, *arg, **kw)
        self.dispatch_subject = self.subject
        self.subject = getattr(self.parent, "subject", None)

    def run_thread(self):
        self.dispatch(self.dispatch_subject)

    def dispatch(self, subject):
        getattr(self, self._dispatcher_class)(parent = self, subject = subject)
