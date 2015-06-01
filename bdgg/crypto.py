import base64
import rsa

import bdgg.config as config

def _mod_init():
    global _priv_key
    with open(config.privatekey, 'rb') as keyfile:
        _priv_key = rsa.PrivateKey.load_pkcs1(keyfile.read())

_mod_init()

def decrypt(msg):
    return rsa.decrypt(base64.b64decode(msg), _priv_key)
