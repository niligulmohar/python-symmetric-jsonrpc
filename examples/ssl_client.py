#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim: set fileencoding=UTF-8 :

import M2Crypto
import symmetricjsonrpc, socket

HOST='localhost'
PORT=4712

class PingRPCClient(symmetricjsonrpc.RPCClient):
    class Request(symmetricjsonrpc.RPCClient.Request):
        def dispatch_request(self, subject):
            # Handle callbacks from the server
            assert subject['method'] == "pingping"
            return "pingpong"

def main():
    ctx = M2Crypto.SSL.Context()
    ctx.set_verify(M2Crypto.SSL.verify_peer | M2Crypto.SSL.verify_fail_if_no_peer_cert, depth=9)
    if ctx.load_verify_locations('server.pem') != 1: raise Exception('No CA certs')
    s = M2Crypto.SSL.Connection(ctx)
    s.connect((HOST, PORT))
    client = PingRPCClient(s)
    res = client.request("ping", wait_for_response=False) == "pong"
    client.notify("shutdown")
    client.shutdown()

if __name__ == '__main__':
    main()
