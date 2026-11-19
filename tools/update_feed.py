#!/usr/bin/env python3
"""Actualiza licitaciones.json a partir del feed Atom oficial de PLACE.

El feed (sindicacion_643) solo contiene las ~50 últimas actualizaciones y no
tiene cabeceras CORS, así que el navegador no puede leerlo directamente.
Este script lo descarga (primera página + páginas anteriores enlazadas con
rel="next"), se queda con las licitaciones PUBLICADAS y las acumula en
licitaciones.json, que la web sirve desde el mismo dominio.

Uso: python tools/update_feed.py
"""
import json, os, sys, time, urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

FEED = "https://contrataciondelestado.es/sindicacion/sindicacion_643/licitacionesPerfilesContratanteCompleto3.atom"
OUT = "licitaciones.json"
MAX_FIRST = 10      # primera ejecución: ~1 día de histórico (cada página ~500 entradas)
MAX_REFRESH = 5     # ejecuciones siguientes (cron cada 4 h; 5 págs ≈ 12 h de margen)
KEEP_DAYS = 21      # sin plazo conocido, se descarta pasado este tiempo
CAP = 8000
TIPOS = {"1": "Suministros", "2": "Servicios", "3": "Obras", "21": "Gestión de servicios públicos",
         "22": "Concesión de servicios", "31": "Concesión de obras", "7": "Administrativo especial",
         "8": "Privado", "40": "Patrimonial", "50": "Otros"}


def local(tag):
    return tag.rsplit("}", 1)[-1]


def find(el, name):
    """Primer descendiente por nombre local (ignora espacios de nombres)."""
    if el is None:
        return None
    for e in el.iter():
        if local(e.tag) == name:
            return e
    return None


def text(el, name):
    e = find(el, name)
    return e.text.strip() if e is not None and e.text and e.text.strip() else None


def fetch(url):
    last = None
    for i in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (licitaciones-bot)"})
            return urllib.request.urlopen(req, timeout=60).read()
        except Exception as e:
            last = e
            time.sleep(3 * (i + 1))
    raise last


def parse(xml_bytes):
    root = ET.fromstring(xml_bytes)
    nxt = None
    for l in root:
        if local(l.tag) == "link" and l.get("rel") == "next":
            nxt = l.get("href")
    out = []
    for entry in root:
        if local(entry.tag) != "entry":
            continue
        cfs = find(entry, "ContractFolderStatus")
        party = find(cfs, "LocatedContractingParty")
        party_name = None
        if party is not None:
            p = find(party, "Party")
            pn = find(p, "PartyName")
            party_name = text(pn, "Name")
        proj = find(cfs, "ProcurementProject")
        budget = find(proj, "BudgetAmount")
        tender = find(cfs, "TenderingProcess")
        dl = find(tender, "TenderSubmissionDeadlinePeriod")
        d, t = text(dl, "EndDate"), text(dl, "EndTime")
        deadline = f"{d}T{t}" if d and t else d
        imp = text(budget, "TaxExclusiveAmount") or text(budget, "TotalAmount")
        link = entry.find("{http://www.w3.org/2005/Atom}link")
        out.append({
            "id": text(entry, "id"),
            "title": text(entry, "title") or text(proj, "Name") or "(sin título)",
            "organismo": party_name,
            "importe": float(imp) if imp else None,
            "estado": text(cfs, "ContractFolderStatusCode"),
            "deadline": deadline,
            "expediente": text(cfs, "ContractFolderID"),
            "tipo": TIPOS.get(text(proj, "TypeCode") or "", None),
            "lugar": text(find(proj, "RealizedLocation"), "CountrySubentity"),
            "cpv": text(find(proj, "RequiredCommodityClassification"), "ItemClassificationCode"),
            "updated": text(entry, "updated"),
            "url": link.get("href") if link is not None else None,
        })
    return out, nxt


def vigente(c, ahora):
    if c["estado"] != "PUB":
        return False
    if c["deadline"]:
        try:
            d = datetime.fromisoformat(c["deadline"])
            if d.tzinfo is None:
                d = d.replace(tzinfo=timezone.utc)
            return d >= ahora
        except ValueError:
            pass
    try:
        u = datetime.fromisoformat(c["updated"])
        return u >= ahora - timedelta(days=KEEP_DAYS)
    except Exception:
        return False


def main():
    previo = {}
    if os.path.exists(OUT):
        with open(OUT, encoding="utf8") as fh:
            previo = {c["id"]: c for c in json.load(fh).get("items", [])}
    paginas = MAX_REFRESH if previo else MAX_FIRST

    nuevos, url = {}, FEED
    for n in range(paginas):
        if not url:
            break
        items, url = parse(fetch(url))
        for c in items:
            # el feed va de más nuevo a más viejo: la primera aparición manda
            nuevos.setdefault(c["id"], c)
        print(f"página {n + 1}: {len(items)} entradas", file=sys.stderr)

    todos = {**previo, **nuevos}   # lo nuevo sustituye a lo previo (cambios de estado)
    ahora = datetime.now(timezone.utc)
    vivos = [c for c in todos.values() if vigente(c, ahora)]
    vivos.sort(key=lambda c: c["updated"] or "", reverse=True)
    vivos = vivos[:CAP]
    with open(OUT, "w", encoding="utf8") as fh:
        json.dump({"generated": ahora.isoformat(timespec="seconds"), "items": vivos},
                  fh, ensure_ascii=False, separators=(",", ":"))
    print(f"{len(vivos)} licitaciones publicadas en {OUT}", file=sys.stderr)


if __name__ == "__main__":
    main()
