import json

CONFIG_KEYS = [
    'filepath',         #local log directory
    'port',             #listening port
    'linelimit',        #hard limit on lines sent
    'connectionlimit',  #limit on how many active sessions an IP is allowed. not implemented
    'rebuildinterval',  #how often to refresh log directories in ms
]

def _mod_init():
    with open('config.json') as json_data:
        data = json.load(json_data)

    for key in CONFIG_KEYS:
        globals()[key] = data[key]

_mod_init()
