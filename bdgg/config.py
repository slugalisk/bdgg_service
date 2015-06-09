import json
import os

CONFIG_KEYS = [
    'filepath',             #local log directory
    'port',                 #listening port
    'linelimit',            #hard limit on lines sent
    'connectionlimit',      #limit on how many active sessions an IP is allowed. not implemented
    'rebuildinterval',      #how often to refresh log directories in seconds
    'privatekey',           #private keyfile used to decrypt sensitive message data
    'userfile',             #file used to store users' state
    'persistusersinterval', #how often to save user state file in seconds
    'debug',                #enable debug logging
    #home,                  #automatically set to app root directory
]

PATH_KEYS = { 'filepath', 'privatekey', 'userfile' }

def _mod_init():
    homepath = os.path.join(os.path.dirname(os.path.realpath(__file__)), "../")
    globals()['home'] = homepath

    configpath = os.path.join(homepath, "config.json")

    with open(configpath) as json_data:
        data = json.load(json_data)

    for key in CONFIG_KEYS:
        val = data.get(key, None)
        globals()[key] = os.path.join(homepath, val) if key in PATH_KEYS else val

_mod_init()
