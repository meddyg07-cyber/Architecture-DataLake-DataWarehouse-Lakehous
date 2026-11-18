"""Petit client de l'API REST NiFi 2.x (bibliothèque standard uniquement).

Identifiants : variables NIFI_USER / NIFI_PASS, sinon relus dans les journaux NiFi locaux
(identifiants générés au 1er démarrage). Rien n'est écrit sur disque.
"""
import json
import os
import re
import ssl
import urllib.parse
import urllib.request
from pathlib import Path

BASE = "https://localhost:8443/nifi-api"
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE   # certificat auto-signé local


def _creds():
    u, p = os.environ.get("NIFI_USER"), os.environ.get("NIFI_PASS")
    if u and p:
        return u, p
    txt = "".join(f.read_text(errors="ignore") for f in Path("/opt/nifi/logs").glob("nifi-app*.log"))
    return (re.findall(r"Generated Username \[([^\]]+)\]", txt)[-1],
            re.findall(r"Generated Password \[([^\]]+)\]", txt)[-1])


class NiFi:
    def __init__(self):
        u, p = _creds()
        data = urllib.parse.urlencode({"username": u, "password": p}).encode()
        req = urllib.request.Request(BASE + "/access/token", data=data,
                                     headers={"Content-Type": "application/x-www-form-urlencoded"})
        self.token = urllib.request.urlopen(req, context=CTX).read().decode()

    def call(self, method, path, body=None, raw=False):
        req = urllib.request.Request(BASE + path, method=method,
                                     data=json.dumps(body).encode() if body is not None else None,
                                     headers={"Authorization": "Bearer " + self.token,
                                              "Content-Type": "application/json"})
        try:
            r = urllib.request.urlopen(req, context=CTX).read()
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"{method} {path} → {e.code} {e.read().decode()[:500]}")
        return r if raw else (json.loads(r) if r else None)

    get = lambda self, p: self.call("GET", p)
    post = lambda self, p, b: self.call("POST", p, b)
    put = lambda self, p, b: self.call("PUT", p, b)
