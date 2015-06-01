import json
from tornado.httpclient import AsyncHTTPClient

import bdgg.config as config

_allusers = {}
_change_handlers = set()

def _wrap_user_cb(func):
    def handle_response(response):
        if response.error:
            print "Error: ", response.error
        else:
            user_json = json.loads(response.body)
            user = User.from_json(user_json)
            return func(user)
    return handle_response

def _get_user(sid, callback):
    headers = {'Cookie': 'sid=%s' % sid}
    client = AsyncHTTPClient()
    return client.fetch('https://www.destiny.gg/profile/info', _wrap_user_cb(callback), headers=headers)

def _notify_change():
    for cb in _change_handlers:
        try:
            cb()
        except:
            pass

def add(user):
    current = _allusers.get(user.username, None)
    if user != current:
        _allusers[user.username] = user
        if config.debug: print "add user: %s" % user
        _notify_change()

def delete(user):
    current = _allusers.pop(user.username, None)
    if current != None:
        if config.debug: print "del user: %s" % user
        _notify_change()

def update(sid):
    _get_user(sid, add)

def remove(sid):
    _get_user(sid, delete)

def get_all_dict():
    return {k: _allusers[k].__dict__ for k in _allusers.keys()}

def add_change_handler(callback):
    _change_handlers.add(callback)

def remove_change_handler(callback):
    _change_handlers.discard(callback)

class User:
    def __init__(self, username, country):
        self.username = username
        self.country = country

    @classmethod
    def from_json(cls, user_json):
        return cls(user_json['username'], user_json['country'])

    def __str__(self):
        return "User(%s, %s}" % (self.username, self.country)

    def __eq__(self, other):
        return (isinstance(other, self.__class__) and
            self.__dict__ == other.__dict__)

    def __ne__(self, other):
        return not self == other
