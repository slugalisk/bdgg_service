# server backend for better destiny.gg

import time
import datetime
import os
import json
import re
import random
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.websocket

################################################################################################
##                                                                                            ##
##                                CONFIGURATION VARIABLES                                     ##
##                                                                                            ##
################################################################################################


filepath = '/srv/www/overrustlelogs.net/public/_public/Destinygg chatlog/'  # local log directory
port = 13373                        #listening port
linelimit = 200                     #hard limit on lines sent. currently not implemented.
connectionlimit = 1                 #limit on how many active sessions an IP is allowed

################################################################################################
################################################################################################

allowedremaining = {}
ipident = {}
banned = set()

class LogSystem:
    def builddir(self):
        self.dirtree = {}
        self.dirtreecase = {}

        for directory in os.listdir(self.toppath):
            monthpath = self.toppath + directory + '/userlogs/'
            self.dirtree[directory] = [x.upper() for x in sorted(os.listdir(monthpath))]
            self.dirtreecase[directory] = [x for x in sorted(os.listdir(monthpath))]

    def refreshtoday(self):
        self.today = datetime.datetime.now()

    def __init__(self, path='/'):
        self.toppath = path
        self.today = datetime.datetime.now()
        print("Building directory index...")
        self.builddir()

    def SearchName(self, myname, months=0):     #returns found name, month string, and month number
        nmonth = months
        if nmonth == 0:     #check if name is in current month
            monthpath = self.toppath + self.today.strftime("%B") + ' ' + str(self.today.year) + '/userlogs/'
            dirlist = sorted(os.listdir(monthpath))
            names = [x.upper() for x in dirlist]
            if myname.upper() in names:     #match found! break out of loop with new name
                return dirlist[names.index(myname.upper())], self.today.strftime("%B") + ' ' + str(self.today.year), 0
            else:
                nmonth += 1

        while 1:    #I did this with a loop rather than iterating keys to insure order
            prvmonth = self.today - datetime.timedelta(weeks=4*nmonth)
            dirkey = prvmonth.strftime('%B') + ' ' + str(prvmonth.year)
            if not dirkey in self.dirtree:  #month not found
                return None, None, None
            else:   #found month
                if myname.upper() in self.dirtree[dirkey]:  #found the name, return it
                    return self.dirtreecase[dirkey][self.dirtree[dirkey].index(myname.upper())], dirkey, nmonth
                else:       #name not found in this month, move on
                    nmonth += 1

    def GetLastLines(self, username, lines = 1):    #case-insensitive, searches all months, returns list of lines or None
        myname = username + '.txt'
        monthpath = self.toppath + self.today.strftime("%B") + ' ' + str(self.today.year) + '/userlogs/'
        prvmonth = 0
        lastlines = []
        nlines = lines

        try:
            with open(monthpath + myname, 'r') as fh:  #try simplest case first
                splitvar = fh.read().split('\n')

                lastlines += splitvar[(lines*-1-1):-1]
                if len(lastlines) >= lines:
                    return lastlines
                else:
                    nlines = lines - len(lastlines)
        except IOError:     #didn't find the name, try to find a case-insensitive match on all previous months
            myname, monthstr, prvmonth = self.SearchName(myname, prvmonth)
            if not myname:
                return None

        prvmonth = 0
        while nlines > 0:
            myname, monthstr, prvmonth = self.SearchName(myname, prvmonth)
            if not myname:
                return lastlines
            prvmonth += 1

            try:
                with open(self.toppath + monthstr + '/userlogs/' + myname, 'r') as fh:
                    splitvar = fh.read().split('\n')

                    lastlines = splitvar[(nlines*-1-1):-1] + lastlines
                    if len(lastlines) >= lines:
                        return lastlines
                    else:
                        nlines = lines - len(lastlines)
            except IOError:
                print('something bad heppen')   #this should never, ever happen
                return None

        return lastlines

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

            if match:
                if not type:
                    addyear = str(DestinyLog.today.year) + ' ' + match.group(1)
                    dtt = time.strptime(addyear, '%Y %b %d %H:%M:%S UTC')
                elif type == 1:
                    dtt = time.strptime(match.group(1), '%b %d %Y %H:%M:%S UTC')
                elif type == 2:
                    dtt = time.strptime(match.group(1), '[%m/%d/%Y %I:%M:%S %p]')

                out.append(str(dtt.tm_sec + dtt.tm_min*60 + dtt.tm_hour*3600 + dtt.tm_yday*86400 + (dtt.tm_year-2010)*31536000))
        return out

def TimeStr():
    return '['+str(datetime.datetime.now()).split('.',1)[0]+'] '

class SocketHandler(tornado.websocket.WebSocketHandler):
    def check_origin(self, origin):
        return True

    def SendError(self, errstring):
        self.write_message({"Type" : "e", "Error" : errstring})
        print(errstring)

    def open(self):
        global allowedremaining
        global ipident
        global banned
        self.hoststr = ''
        self.ipaddr = self.request.remote_ip

        if self.ipaddr in banned:
            banned.remove(self.ipaddr)

        with open('banned.txt', 'r+') as fh:
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
                ipident[self.ipaddr] = NameGen.generate(self.ipaddr)
            self.hoststr = "(%s [%s]):" % (ipident[self.ipaddr], self.ipaddr)

        print(TimeStr() + self.hoststr + " new connection.")   #supress connection echo, because of new client model

    def on_close(self):
        print(TimeStr() + self.hoststr + " connection closed.")
        pass

    def on_message_proc(self, message):
        try:
            json_data = json.loads(message)
        except ValueError:
            print("JSON parse failed.")
            return

        if "Number" in json_data:
            if int(json_data["Number"]) > linelimit:
                self.SendError("Too many lines.")
                if "Session" in json_data:
                    return json_data["Session"]

        if "QueryType" in json_data:
            if json_data["QueryType"] == "s":
                if "Name" in json_data and "Number" in json_data:
                    if re.search(r'^\d+$', json_data["Number"]) \
                    and re.search(r'^[\w\d]+$', json_data["Name"]):
                        lines = DestinyLog.GetLastLines(json_data["Name"], int(json_data["Number"]))
                        if not lines:
                            self.SendError("Name not found.")
                        else:
                            times = DestinyLog.ParseTimestamps(lines)
                            self.write_message({"Type": "s", "Data": json.dumps(lines), "Times": json.dumps(times)})
                else:
                    self.SendError("Did not understand query.")
            elif json_data["QueryType"] == "m":
                if "Names" in json_data and "Number" in json_data:
                    if re.search(r'^\d+$', json_data["Number"]):
                        num = int(json_data["Number"])
                        tlines = []
                        ttimes = []
                        for name in json_data["Names"]:
                            if re.search(r'^[\w\d]+$', name):
                                lines = DestinyLog.GetLastLines(name, num)
                                if not lines:
                                    self.SendError("Name not found.")
                                    break
                                else:
                                    tlines += lines
                                    ttimes += DestinyLog.ParseTimestamps(lines)
                            else:
                                self.SendError("Malformed name string.")
                                break

                        ttimes, tlines = [list(x) for x in zip(*sorted(zip(ttimes, tlines), key=lambda pair: pair[0]))]
                        self.write_message({"Type": "s", "Data": json.dumps(tlines[-num:]), "Times": json.dumps(ttimes[-num:])})


            else:
                self.SendError("Did not understand query.")

        if "Session" in json_data:
            return json_data["Session"]
            #self.write_message("message received")

    def on_message(self,message):
        global banned
        if self.ipaddr in banned:
            return

        session = self.on_message_proc(message)

        if session:
            print("%s%s %s %s" % (TimeStr(), session, self.hoststr, format(message)))
        else:
            print("%s%s %s" % (TimeStr(), self.hoststr, format(message)))




class WordGen:    #pseudorandom name generator

    grammar = { '{lexpat}' : [  '{c}{v}{lexpat}',
                                '{v}{c}{lexpat}',
                                '{word}',
                                ''
                                ],
                '{c}' : 'bcdfghjklmnpqrstvwxyz',
                '{v}' : 'aeiouy',
                '{word}' : [    '{c}{v}{c}{lexpat}',
                                '{v}{c}{v}{lexpat}',
                                ]
                }
    grammarindex = sorted(grammar.keys())

    weights = { '{lexpat}' : [0.25,0.25,0.15,1],
                '{c}' : [0.0477, 0.0477,0.0477,0.0477,0.0476,
                        0.0476,0.0476,0.0476,0.0476,0.0476,
                        0.0476,0.0476,0.0476,0.0476,0.0476,
                        0.0476,0.0476,0.0476,0.0476,0.0476,
                        0.0476
                        ],
                '{v}' : [   0.1667,0.1667,0.1667,0.1666,0.1667,
                            0.1666
                        ],
                '{word}' : [0.5,0.5]
                }

    def getToken(self, token):
        num = random.random()
        acc = 0.0
        i = 0

        while num > acc:
            acc += WordGen.weights[token][i]
            i += 1

        i -= 1
        return WordGen.grammar[token][i]


    def generate(self, rseed):
        random.seed(rseed)
        word = ''

        while len(word) < 4:
            word += '{word}'
            flag = 1
            while flag:
                flag = 0
                for key in WordGen.grammarindex:
                    index = word.find(key)

                    while index != -1:
                        word = word.replace(key, self.getToken(key), 1)
                        index = word.find(key)
                        flag = 1
        return word[:10]

NameGen = WordGen()
DestinyLog = LogSystem(filepath)

def rebuildlogsystem():
    print("Rebuilding directory index...")
    DestinyLog.builddir()
    DestinyLog.refreshtoday()

if __name__ == "__main__":
    tornado.options.parse_command_line()
    app = tornado.web.Application(handlers=[(r"/ws",SocketHandler)])
    server = tornado.httpserver.HTTPServer(app)
    server.listen(port)
    tornado.ioloop.PeriodicCallback(rebuildlogsystem, 3600000).start()    #rebuild log directory index every hour
    tornado.ioloop.IOLoop.instance().start()
