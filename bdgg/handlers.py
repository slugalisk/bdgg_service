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

        with open('banned.txt', 'a+') as fh:
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
            if int(json_data["Number"]) > config.linelimit:
                self.SendError("Too many lines.")
                if "Session" in json_data:
                    return json_data["Session"]

        if "QueryType" in json_data:
            if json_data["QueryType"] == "s":
                if "Name" in json_data and "Number" in json_data:
                    if re.search(r'^[\w\d]+$', json_data["Name"]):
                        lines = DestinyLog.GetLastLines(json_data["Name"], int(json_data["Number"]))
                        if not lines:
                            self.SendError("Name not found.")
                        else:
                            times = DestinyLog.ParseTimestamps(lines)
                            self.write_message({"Type": "s", "Data": lines, "Times": times})
                else:
                    self.SendError("Did not understand query.")
            elif json_data["QueryType"] == "m":
                if "Names" in json_data and "Number" in json_data:
                    num = int(json_data["Number"])
                    tlines = []
                    ttimes = []
                    for name in json_data["Names"]:
                        if re.search(r'^[\w\d]+$', name):
                            lines = DestinyLog.GetLastLines(name, num)
                            if lines:
                                tlines += lines
                                ttimes += DestinyLog.ParseTimestamps(lines)
                        else:
                            self.SendError("Malformed name string.")
                            break

                    messages = [list(x) for x in zip(*sorted(zip(ttimes, tlines), key=lambda pair: pair[0]))]
                    if messages:
                        ttimes, tlines = messages
                        self.write_message({"Type": "s", "Data": tlines[-num:], "Times": ttimes[-num:]})
                    else:
                        self.SendError("Names not found.")
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

