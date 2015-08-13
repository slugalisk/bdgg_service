# server backend for better destiny.gg

import time
import datetime
import httplib
import json
import os
import re
from StringIO import StringIO
import sys
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web

import bdgg.config as config
import bdgg.handlers
import destinygg.users

class LogSystem:
    def __init__(self, path='/'):
        self.toppath = path
        self.today = datetime.datetime.now()
        print("Building directory index...")
        self.builddir()

    def GetLastLines(self, username, lines = 1):    #case-insensitive, searches all months, returns list of lines or None
        conn = httplib.HTTPConnection(config.overrustlelogs_host)
        conn.request("GET", '/api/v1/stalk/Destinygg chatlog/' + username + '.json?limit=' + lines)
        response = conn.getresponse()
        data = json.load(StringIO(response.read()))
        conn.close()

        if 'lines' in data:
            return data['lines']
        else:
            return None

    def ParseTimestamps(self, lines):  #returns timestamps for lines
        out = []
        for line in lines:
            type = None
            match = re.search('(\w\w\w \d?\d \d?\d:\d\d:\d\d UTC)', line)
            if not match:
                match = re.search('(\w\w\w \d?\d \d\d\d\d \d?\d:\d\d:\d\d UTC)', line)
                type = 1
            if not match:
                match = re.search('(\[\d\d/\d\d/\d\d\d\d \d?\d:\d\d:\d\d (?:AM|PM)\])', line)
                type = 2
            if not match:
                match = re.search('(\[\d\d\d\d-\d\d-\d\d \d?\d:\d\d:\d\d UTC\])', line)
                type = 3

            if match:
                if not type:
                    addyear = str(DestinyLog.today.year) + ' ' + match.group(1)
                    dtt = time.strptime(addyear, '%Y %b %d %H:%M:%S UTC')
                elif type == 1:
                    dtt = time.strptime(match.group(1), '%b %d %Y %H:%M:%S UTC')
                elif type == 2:
                    dtt = time.strptime(match.group(1), '[%m/%d/%Y %I:%M:%S %p]')
                elif type == 3:
                    dtt = time.strptime(match.group(1), '[%Y-%m-%d %H:%M:%S UTC]')

                out.append(str(dtt.tm_sec + dtt.tm_min*60 + dtt.tm_hour*3600 + dtt.tm_yday*86400 + (dtt.tm_year-2010)*31536000))
        return out

DestinyLog = LogSystem(config.filepath)

#if os.access(config.userfile, os.R_OK):
with open(config.userfile, 'a+') as uf:
    uf.seek(0)
    try:
        userdata = json.load(uf)
        for user_json in userdata.values():
            user = destinygg.users.User.from_json(user_json)
            destinygg.users.add(user)
    except ValueError as e:
        print "Error parsing userfile: ", e

def persist_users():
    with open(config.userfile, 'w') as uf:
        user_dict = {}
        uf.write(json.dumps(destinygg.users.get_all_dict()))

def on_change():
    print "on_change"

destinygg.users.add_change_handler(on_change)

if __name__ == "__main__":
    tornado.options.parse_command_line()
    app = tornado.web.Application([
        (r"/ws" , bdgg.handlers.SocketHandler, {"destinylog": DestinyLog})
    ])
    server = tornado.httpserver.HTTPServer(app)
    server.listen(config.port)
    tornado.ioloop.PeriodicCallback(persist_users, config.persistusersinterval).start()
    tornado.ioloop.IOLoop.instance().start()
