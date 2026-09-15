#!/usr/bin/env python3
"""¿Saldría más barato comprando desde el otro país?

Wizz cotiza el MISMO asiento en la divisa del país de salida, y no siempre al
mismo cambio: GDN→ALC vale 409 PLN (94,24 €) o 89,99 € según cómo se pregunte.
El bot ya pide en euros, pero eso era una suposición. Esto lo comprueba de
verdad, una vez al día, y avisa si alguna vez la divisa local pasa a ganar.

MARGEN existe porque comparar al cambio del BCE engaña: pagando en moneda
extranjera el banco cobra su comisión (1,5-3 % es lo normal). Para que compense
de verdad, la tarifa local tiene que ganar por más que eso.
"""
import time

from botviajes.fx import a_euros
from botviajes.providers import get_provider

MARGEN = 0.03      # 3 %: por debajo de eso se lo come la comisión de la tarjeta
ESPERA = 3.0       # segundos entre consultas, para no molestar a Wizz


def _leer(d, co, cd, fecha):
    """Precio firme más barato de ese tramo concreto en la respuesta."""
    fuera = []
    for clave in ("outboundFlights", "returnFlights"):
        for f in (d or {}).get(clave, []) or []:
            if f.get("departureStation") != co or f.get("arrivalStation") != cd:
                continue
            if not (f.get("departureDate") or "").startswith(fecha):
                continue
            p = f.get("price") or {}
            if f.get("priceType") == "price" and p.get("amount"):
                fuera.append((float(p["amount"]), p.get("currencyCode")))
    return min(fuera) if fuera else None


def comparar(co, cd, fecha, adults=2, prov=None):
    """Devuelve (euros, local_en_euros, divisa_local) o None si no hay precio."""
    w = prov or get_provider("wizz")
    # Wizz devuelve los importes en la divisa de salida del PRIMER tramo, así que
    # cambiando el orden se pregunta el precio en una divisa o en la otra.
    ida = {"departureStation": co, "arrivalStation": cd, "from": fecha, "to": fecha}
    vuelta = {"departureStation": cd, "arrivalStation": co, "from": fecha, "to": fecha}
    delante = ida if w._en_euros(co) else vuelta
    detras = ida if w._en_euros(co) else vuelta

    def pedir(tramos):
        return w._post("/search/timetable",
                       {"flightList": tramos, "priceType": "regular",
                        "adultCount": adults, "childCount": 0, "infantCount": 0})

    en_euros = _leer(pedir([delante, ida] if delante is not ida else [ida]), co, cd, fecha)
    time.sleep(ESPERA)
    otra = [vuelta, ida] if w._en_euros(co) else [ida]
    en_local = _leer(pedir(otra), co, cd, fecha)
    if not en_euros or not en_local:
        return None
    e = a_euros(*en_euros)
    l = a_euros(*en_local)
    if e is None or l is None:
        return None
    return e, l, en_local[1]


def revisar(rutas, adults=2):
    """Compara varias rutas. Devuelve la lista de las que salen más baratas fuera."""
    w = get_provider("wizz")
    gangas = []
    for co, cd, fecha in rutas:
        try:
            r = comparar(co, cd, fecha, adults, prov=w)
        except Exception as e:
            print("  [divisas] %s→%s: %s" % (co, cd, str(e)[:70]))
            continue
        if not r:
            continue
        eur, loc, div = r
        ahorro = eur - loc
        print("  [divisas] %s→%s  euros %.2f € | %s %.2f €  -> %s"
              % (co, cd, eur, div, loc,
                 "gana el euro" if ahorro <= 0 else "gana %s por %.2f €" % (div, ahorro)))
        if ahorro > eur * MARGEN:
            gangas.append({"ruta": "%s→%s" % (co, cd), "fecha": fecha, "eur": eur,
                           "local": loc, "divisa": div, "ahorro": ahorro})
        time.sleep(ESPERA)
    return gangas


def texto_aviso(gangas):
    if not gangas:
        return None
    l = ["💱 <b>Sale más barato pagando en otra moneda</b>", ""]
    for g in gangas:
        l.append("• <b>%s</b> (%s): %.2f € en euros, pero <b>%.2f €</b> pagando "
                 "en %s → ahorras <b>%.2f €</b> por persona."
                 % (g["ruta"], g["fecha"], g["eur"], g["local"], g["divisa"], g["ahorro"]))
    l += ["", "Ya descontada la comisión típica de tarjeta (3 %). Para pagar en esa "
          "moneda hay que cambiar el país en la web de Wizz antes de reservar."]
    return "\n".join(l)


if __name__ == "__main__":
    import yaml
    ws = (yaml.safe_load(open("watches.yaml")) or {}).get("watches", [])
    rutas = [(w["origin"], w["destination"], w["date"]) for w in ws
             if "wizz" in (w.get("providers") or [])]
    print("Comparando %d rutas de Wizz (euros vs divisa local)\n" % len(rutas))
    g = revisar(rutas)
    print()
    print(texto_aviso(g) or "Ninguna sale más barata en moneda local. El euro gana.")
