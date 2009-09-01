Python Symmetric JSON-RPC

"A more beautiful JSON-RPC implemenation in python."

A JSON-RPC (see http://json-rpc.org) implementation for Python, with
the following features:

 * Symmetric - both the connecting and the listening process can send
   and receive method calls, there is no specific "server" or "client"
   process, and no difference between the two connection ends apart
   from who initiates the connection.

 * Asynchronous - calls can be interlieved with new calls initiated
   before a previous call has returned.

 * Thread-safe - calls to the remote side can be done from multiple
   threads without any locking.

 * Transport agnostic - can run on top of anything that resembles a
   socket the slightest (e.g. OpenSSL)

What this really drills down to is that this library implements the
full specification of JSON-RPC over sockets, something no other
implementation of JSON-RPC for Python does.


For usage details, look at the examples in the "examples" directory.
