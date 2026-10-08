"""Aggiorna guardoserie + sc in domains.json. Solo stdlib, idempotente.

- guardoserie: estratto dal link in https://guardaserie.foo/
- sc: segue il redirect del dominio salvato (il vecchio porta al nuovo)
- Salva solo se il candidato risponde HTTP 200, altrimenti tiene il vecchio.
"""
import json
import re
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

BASE = Path(__file__).resolve().parent.parent
JSON_PATH = BASE / "domains.json"
TIMEOUT = 20
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) domains-bot/1.0"}
PARKING = ("domain for sale", "buy this domain", "parked domain", "domain parking")


def fetch(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=TIMEOUT)


def origin(url):
    p = urlsplit(url)
    return urlunsplit((p.scheme, p.netloc, "", "", "")).rstrip("/")


def alive(url):
    try:
        with fetch(url) as r:
            if r.status != 200:
                return False
            body = r.read(200_000).decode("utf-8", "ignore").lower()
        return not any(k in body for k in PARKING)
    except Exception as e:
        print(f"check fallito per {url}: {e}")
        return False


def resolve_guardoserie():
    with fetch("https://guardaserie.foo/") as r:
        html = r.read(500_000).decode("utf-8", "ignore")
    for h in re.findall(r'href=["\'](https?://[^"\']+)["\']', html, re.I):
        low = h.lower()
        if "guardaserie.foo" in low or "guardaplay" in low:
            continue
        if "guardoserie" in low or "guardaserie" in low:
            return origin(h)
    print("nessun link guardoserie trovato in guardaserie.foo")
    return None


def resolve_sc(current):
    with fetch(current) as r:  # urllib segue i redirect: l'URL finale e' il nuovo dominio
        new = origin(r.geturl())
    print(f"sc: {current} -> {new}")
    return new


def main():
    data = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    for key, resolver in (("guardoserie", lambda: resolve_guardoserie()),
                          ("sc", lambda: resolve_sc(data["sc"]))):
        try:
            new = resolver()
        except Exception as e:
            print(f"{key}: errore, tengo il vecchio ({e})")
            continue
        if new and new != data.get(key) and alive(new):
            print(f"{key}: {data.get(key)} -> {new}")
            data[key] = new
        else:
            print(f"{key}: nessun cambio (attuale {data.get(key)})")
    JSON_PATH.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
