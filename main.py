# server backend for better destiny.gg

import time
import datetime
import os
import re
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web

import bdgg.config as config
import bdgg.handlers

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

DestinyLog = LogSystem(config.filepath)

def rebuildlogsystem():
    print("Rebuilding directory index...")
    DestinyLog.builddir()
    DestinyLog.refreshtoday()

if __name__ == "__main__":
    tornado.options.parse_command_line()
    app = tornado.web.Application([
        (r"/ws" , bdgg.handlers.SocketHandler, {"destinylog": DestinyLog})
    ])
    server = tornado.httpserver.HTTPServer(app)
    server.listen(config.port)
    tornado.ioloop.PeriodicCallback(rebuildlogsystem, config.rebuildinterval).start()
    tornado.ioloop.IOLoop.instance().start()
