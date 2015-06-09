import datetime
import json
import re

from twisted.internet import task
from twisted.internet.defer import inlineCallbacks, returnValue
from autobahn import wamp
from autobahn.twisted.util import sleep
from autobahn.twisted.wamp import ApplicationSession
from autobahn.wamp.exception import ApplicationError
from autobahn.wamp.types import CallResult, SubscribeOptions

import bdgg.config as config
import bdgg.crypto as crypto
import bdgg.wordgen as wordgen
from bdgg.log import LogSystem
import destinygg.users

allowedremaining = {}
ipident = {}
banned = set()

@wamp.error(u"bdgg.error.name_not_found")
class NameNotFoundError(ApplicationError):
    def __init__(self, *args, **kwargs):
        ApplicationError.__init__(self, u"bdgg.error.name_not_found", *args, **kwargs)

@wamp.error(u"bdgg.error.malformed_name")
class MalformedNameError(ApplicationError):
    def __init__(self, *args, **kwargs):
        ApplicationError.__init__(self, u"bdgg.error.malformed_name", *args, **kwargs)

def TimeStr():
    return '['+str(datetime.datetime.now()).split('.',1)[0]+'] '

class SocketHandler(ApplicationSession):
    def __init__(self, *args, **kwargs):
        ApplicationSession.__init__(self, *args, **kwargs)
        self.__destinylog = LogSystem(config.filepath)

    def initialize(self, destinylog):
        self.__destinylog = destinylog

    def check_origin(self, origin):
        return True

    def SendError(self, errstring):
        self.write_message({"Type" : "e", "Error" : errstring})
        print(errstring)

    @inlineCallbacks
    def onJoin(self, details):
        if config.debug: print "join from: %s" % details

        def onhello(QueryType, Name, Number, Names=None, Session=None):
            if config.debug: print "hello received: %s %s %s %s" % (QueryType, Name, Number, Names)
        yield self.subscribe(onhello, 'bdgg.hello')

        def onserverhello(QueryType, Name, Number, Names=None, Session=None):
            if config.debug: print "server hello received: %s %s %s %s" % (QueryType, Name, Number, Names)
        yield self.subscribe(onserverhello, 'bdgg.server.hi')

        yield self.register(self.onstalk, 'bdgg.stalk')

        yield self.register(self.on_flair_get_all, 'bdgg.flair.get_all')
        yield self.register(self.on_flair_remove, 'bdgg.flair.remove')
        yield self.register(self.on_flair_update, 'bdgg.flair.update')

    def open(self):
        global allowedremaining
        global ipident
        global banned
        self.hoststr = ''
        self.ipaddr = self.request.remote_ip

        if self.ipaddr in banned:
            banned.remove(self.ipaddr)

        with open('banned.txt', 'a+') as fh:
            fh.seek(0)
            for item in fh:
                item = item.replace('\n','')
                match = re.match(item, str(self.ipaddr))
                if match:
                    self.close()
                    banned.add(self.ipaddr)
                    return


        if self.ipaddr == '::1':
            self.hoststr = "(localhost):"
        else:
            if not self.ipaddr in ipident:
                ipident[self.ipaddr] = wordgen.generate(self.ipaddr)
            self.hoststr = "(%s [%s]):" % (ipident[self.ipaddr], self.ipaddr)

        print(TimeStr() + self.hoststr + " new connection.")   #supress connection echo, because of new client model

    def on_close(self):
        print(TimeStr() + self.hoststr + " connection closed.")
        pass

    def onstalk(self, QueryType, Name=None, Number=3, Names=None, Session=None):
        if config.debug: print "stalk received: %s %s %s %s" % (QueryType, Name, Number, Names)

        if Number > config.linelimit:
            raise ApplicationError('bdgg.error.too_many_lines', 'Too many lines')
            #if "Session" in json_data:
            #    return json_data["Session"]

        if QueryType == 's':
            if re.search(r'^[\w\d]+$', Name):
                lines = self.__destinylog.GetLastLines(Name, Number)
                if not lines:
                    raise NameNotFoundError("Name not found: %s. Remember nicks are case-sensitive." % Name)
                else:
                    times = self.__destinylog.ParseTimestamps(lines)
                    return CallResult(Type='s', Data=lines, Times=times)
        elif QueryType == 'm':
            if Names:
                num = max(1, Number)
                tlines = []
                ttimes = []
                for name in Names:
                    if re.search(r'^[\w\d]+$', name):
                        lines = self.__destinylog.GetLastLines(name, num)
                        if lines:
                            tlines += lines
                            ttimes += self.__destinylog.ParseTimestamps(lines)
                    else:
                        raise MalformedNameError()

                messages = [list(x) for x in zip(*sorted(zip(ttimes, tlines), key=lambda pair: pair[0]))]
                if messages:
                    ttimes, tlines = messages
                    return CallResult(Type='s', Data=tlines[-num:], Times=ttimes[-num:])
                else:
                    raise NameNotFoundError("Nicks not found. Remember nicks are case-sensitive.")
        else:
            raise ApplicationError(ApplicationError.INVALID_ARGUMENT, 'QueryType')

        #if "Session" in json_data:
        #    return json_data["Session"]
        #    #self.write_message("message received")

    def on_flair_get_all(self):
        return CallResult(users=destinygg.users.get_all_dict())

    @inlineCallbacks
    def on_flair_remove(self, username, esid):
        if config.debug: print "on_flair_remove: %s %s" % (username, esid)
        sid = crypto.decrypt(esid)
        removed = yield destinygg.users.remove(sid)
        if removed:
            self._publish_flair_refresh()
            returnValue(True)
        returnValue(False)

    @inlineCallbacks
    def on_flair_update(self, username, esid):
        if config.debug: print "on_flair_update: %s %s" % (username, esid)
        sid = crypto.decrypt(esid)
        updated = yield destinygg.users.update(sid)
        if updated:
            self._publish_flair_refresh()
            returnValue(True)
        returnValue(False)

    def _publish_flair_refresh(self):
        self.publish('bdgg.flair.refresh', users=destinygg.users.get_all_dict())

    def on_message(self,message):
        global banned
        if self.ipaddr in banned:
            return

        session = self.on_message_proc(message)

        if config.debug:
            if session:
                print("%s%s %s %s" % (TimeStr(), session, self.hoststr, format(message)))
            else:
                print("%s%s %s" % (TimeStr(), self.hoststr, format(message)))

_DestinyLog = LogSystem(config.filepath)

#if os.access(config.userfile, os.R_OK):
with open(config.userfile, 'a+') as uf:
    uf.seek(0)
    try:
        userdata = json.load(uf)
        for user_json in userdata.values():
            user = destinygg.users.User.from_json(user_json)
            destinygg.users.add(user)
    except ValueError as e:
        print "Error parsing userfile: %s" % e

def rebuildlogsystem():
    print("Rebuilding directory index...")
    _DestinyLog.builddir()
    _DestinyLog.refreshtoday()

def persist_users():
    with open(config.userfile, 'w') as uf:
        user_dict = {}
        uf.write(json.dumps(destinygg.users.get_all_dict()))

#def on_change():
#    print "on_change"
#
#destinygg.users.add_change_handler(on_change)

task.LoopingCall(rebuildlogsystem).start(config.rebuildinterval)
task.LoopingCall(persist_users).start(config.persistusersinterval)
