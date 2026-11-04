"""Regenera los menús 1200-2400 kcal usando solo platillos (sin bebidas ni acompañamientos)."""
import json
import random
import re

import database
from menu_tab import DIAS_SEMANA

# Bebidas: regla del catálogo + smoothies/shakes/lattes/bebidas Silk
BEBIDA = re.compile(
    r"\b(agua|te|licuado|jugo|nectar|cafe|atole|champurrado|limonada|"
    r"infusion|bebida|vitamina|smoothie|shake|latte|cappuccino|mojito|"
    r"fizz|kombucha|matcha|malteada|chai|soda)\b")

# Acompañamientos: frutas sueltas, guarniciones y sopas/cremas solas
ACOMP = re.compile(
    r"^(arroz|pure de|papas? al|frijoles|verduras al|brocoli al|coliflor al|"
    r"nieve|gelatina|pina($| y|,| )|manzana($| al horno| con|,)|naranjas|"
    r"melon|sandia|pera($|,)|platano con yogurt|fresas y|papaya|toronja y|"
    r"fruta con|postre de mango)"
    r"|al vapor"
    r"|^sopa de|^crema de")


def es_platillo(nombre):
    n = nombre.lower()
    return not (BEBIDA.search(n) or ACOMP.search(n))


def kcal_p(p):
    try:
        return float(json.loads(p.get("totales") or "{}").get("energia_kcal") or 0)
    except Exception:
        return 0.0


TIEMPOS = ["Desayuno", "Colación Matutina", "Comida", "Cena"]
PART = [0.25, 0.12, 0.35, 0.28]
NIVELES = [1200, 1500, 1800, 2000, 2200, 2400]
TOL = 0.06
random.seed(2026)

pools = {}
for t in TIEMPOS:
    todos = [p for p in database.get_platillos(t)
             if kcal_p(p) >= 5 and json.loads(p["ingredientes"] or "[]")]
    pools[t] = [p for p in todos if es_platillo(p["nombre"])]
    excluidos = [p["nombre"] for p in todos if not es_platillo(p["nombre"])]
    print(f"{t}: {len(pools[t])} platillos válidos (se quitan {len(excluidos)})")
    for e in excluidos[:8]:
        print(f"    - {e}")
    if len(excluidos) > 8:
        print(f"    ... y {len(excluidos) - 8} más")

complementos = [
    p for p in database.get_platillos()
    if 80 <= kcal_p(p) <= 500 and json.loads(p["ingredientes"] or "[]")
    and es_platillo(p["nombre"])
]
print(f"Complementos válidos: {len(complementos)}")


def elegir(cands, obj, usados, excl):
    c = [p for p in cands if p["nombre"] not in excl] or cands
    c = sorted(c, key=lambda p: (abs(kcal_p(p) - obj), usados.get(p["nombre"], 0)))
    return random.choice(c[:3])


for kcal in NIVELES:
    usados, dias = {}, {}
    for dia in DIAS_SEMANA:
        sel = {i: [] for i in range(4)}
        excl = set()
        for i, (t, f) in enumerate(zip(TIEMPOS, PART)):
            p = elegir(pools[t], kcal * f, usados, excl)
            sel[i].append(p)
            excl.add(p["nombre"])
        for _ in range(30):
            total = sum(kcal_p(p) for ps in sel.values() for p in ps)
            if abs(total - kcal) <= kcal * TOL:
                break
            i = max(range(4), key=lambda k: abs(kcal_p(sel[k][0]) - kcal * PART[k]))
            sel[i][0] = elegir(pools[TIEMPOS[i]], kcal * PART[i], usados, excl)
            excl = {ps[0]["nombre"] for ps in sel.values()}
        for _ in range(3):
            total = sum(kcal_p(p) for ps in sel.values() for p in ps)
            if total >= kcal * (1 - TOL):
                break
            falta = kcal - total
            cands = [c for c in complementos
                     if c["nombre"] not in excl and kcal_p(c) <= falta + 200]
            if not cands:
                break
            comp = min(cands, key=lambda c: (abs(kcal_p(c) - falta),
                                             usados.get(c["nombre"], 0)))
            i = max(range(4),
                    key=lambda k: kcal * PART[k] - sum(kcal_p(p) for p in sel[k]))
            sel[i].append(comp)
            excl.add(comp["nombre"])

        plats, alims = {}, {}
        for i, ps in sel.items():
            plats[i] = " + ".join(p["nombre"] for p in ps)
            alims[i] = [ing for p in ps for ing in json.loads(p["ingredientes"])]
            for p in ps:
                usados[p["nombre"]] = usados.get(p["nombre"], 0) + 1
        dias[dia] = {"platillos": plats, "alimentos": alims}
        total = sum(kcal_p(p) for ps in sel.values() for p in ps)
        print(f"  {dia} [{kcal}]: {total:5.0f} kcal — " +
              " | ".join(plats[i] for i in sorted(plats)))

    prom = sum(
        sum((r.get("energia_kcal") or 0) * r.get("eq_cantidad", 1.0)
            for lst in dias[d]["alimentos"].values() for r in lst)
        for d in DIAS_SEMANA
    ) / 7
    database.guardar_menu_guardado(
        f"Menú {kcal} kcal", round(prom),
        json.dumps({"tiempos": TIEMPOS, "dias": dias}, ensure_ascii=False))
    print(f"  -> «Menú {kcal} kcal» promedio {prom:.0f}\n")

print("=== Plantillas finales ===")
for m in database.get_menus_guardados():
    print(f"  {m['nombre']:18} {m['kcal']:5} kcal")
