import json, threading

class RPCSendMixin(object):
    def __init__(self):
        self._request_id = 0
        self._send_lock = threading.Lock()
    
    def request(self, method, params, id):
        with self._send_lock:            
            self._request_id += 1
            json.json({'method':method, 'params': params, 'id': self._request_id}, self.socket)
            return self._request_id

    def response(self, result, error, id):
        with self._send_lock:            
            json.json({'result':result, 'error': error, 'id': id}, self.socket)

    def notification(self, method, params):
        with self._send_lock:            
            json.json({'method':method, 'params': params}, self.socket)

class RPCRecieveMixin(object):
    def __init__(self):
        self._recv_waiting = {}

    def dispatch(self, value):
        if 'method' in value and 'id' in value:
            self.dispatch_request(value)
        elif 'result' in value:
            self._assert_in('id', value)
            self._assert_in(value['id'], self._recv_waiting)
            with self._recv_waiting[value['id']]:
                self._recv_waiting[value['id']][1] = value
                self._recv_waiting[value['id']][0].notifyAll()
        elif 'method' in value:
            self.dispatch_notification(value)

    def wait_for_response(self, id):
          self._recv_waiting[id] = [threading.Condition(), None]
          try:
              with self._recv_waiting[id]:
                  self._recv_waiting[id].wait()
                  return self._recv_waiting[id][1]
          finally:
              del self._recv_waiting[id]
