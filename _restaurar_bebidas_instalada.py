# -*- coding: utf-8 -*-
"""Restaura las bebidas (agua/licuados del respaldo 3-nov) SOLO en los menus
guardados de una BD destino que NO fueron reescritos desde los PDF (los que
el sitio no puede imprimir). No toca pacientes.
Uso: python _restaurar_bebidas_instalada.py <bd_destino> [--aplicar]
"""
import json
import re
import sqlite3
import sys
import unicodedata
from pathlib import Path

BASE = Path(__file__).parent
RESPALDO = BASE / 'Nutrición_deportiva_respaldo_20261103_163138.db'
DATOS = BASE / '_extraccion_smae' / '_datos_smae.json'
FAMILIAS = ('menú clásico', 'menú de actualidad', 'menú sin gluten',
            'menú vegano', 'menú vegetariano', 'menú lunes')

def es_familia(n):
    return n.strip().lower().startswith(FAMILIAS)

def orden_slot(s):
    return int(s) if str(s).isdigit() else 999

def nombres(lista):
    return [r.get('alimento', '') for r in (lista or [])]

def fusion_slot(lista_vieja, lista_nueva):
    pendientes = list(lista_nueva or [])
    usados = [False] * len(pendientes)
    fusion = []
    for r_v in lista_vieja or []:
        nombre = r_v.get('alimento', '')
        idx = next((j for j, r_n in enumerate(pendientes)
                    if not usados[j] and r_n.get('alimento', '') == nombre), None)
        if idx is None:
            fusion.append(r_v)
        else:
            usados[idx] = True
            fusion.append(pendientes[idx])
    fusion.extend(r for j, r in enumerate(pendientes) if not usados[j])
    return fusion

def suma_kcal(d):
    t = 0.0
    for dia in d['dias'].values():
        for lista in (dia.get('alimentos') or {}).values():
            for r in (lista or []):
                eq = r.get('eq_cantidad')
                t += (r.get('energia_kcal') or 0) * (eq if eq is not None else 1)
    return t

def main():
    destino = sys.argv[1]
    aplicar = '--aplicar' in sys.argv
    con_v = sqlite3.connect(RESPALDO)
    viejo = {n: json.loads(d) for n, d in
             con_v.execute('SELECT nombre, detalle FROM menus_guardados')}
    kcal_vieja = dict(con_v.execute('SELECT nombre, kcal FROM menus_guardados'))
    con_v.close()
    pdf_names = set(json.loads(DATOS.read_text(encoding='utf-8'))['menus'])

    con = sqlite3.connect(destino)
    actuales = {n: json.loads(d) for n, d in
                con.execute('SELECT nombre, detalle FROM menus_guardados')}
    tocados = 0
    for nombre, da in actuales.items():
        if nombre in pdf_names or not es_familia(nombre) or nombre not in viejo:
            continue
        dv = viejo[nombre]
        detalle_n = {'tiempos': da.get('tiempos', dv.get('tiempos')), 'dias': {}}
        cambio = False
        for dia in set(dv['dias']) | set(da['dias']):
            dia_v = dv['dias'].get(dia) or {}
            dia_a = da['dias'].get(dia) or {}
            ali_v = dia_v.get('alimentos') or {}
            ali_a = dia_a.get('alimentos') or {}
            ali_n, pla_n = {}, {}
            for slot in sorted(set(ali_v) | set(ali_a), key=orden_slot):
                fus = fusion_slot(ali_v.get(slot), ali_a.get(slot))
                ali_n[slot] = fus
                if nombres(fus) != nombres(ali_a.get(slot)):
                    cambio = True
                if slot in (dia_a.get('platillos') or {}):
                    texto_actual = ' + '.join(nombres(ali_a.get(slot)))
                    if dia_a['platillos'][slot] == texto_actual:
                        pla_n[slot] = ' + '.join(nombres(fus))
                    else:
                        pla_n[slot] = dia_a['platillos'][slot]
            dia_n = {'platillos': pla_n if pla_n else (dia_a.get('platillos') or {}),
                     'alimentos': ali_n}
            for k, v in dia_a.items():
                if k not in ('platillos', 'alimentos'):
                    dia_n[k] = v
            detalle_n['dias'][dia] = dia_n
        if not cambio:
            continue
        tocados += 1
        if aplicar:
            kcal = int(round(suma_kcal(detalle_n)))
            con.execute('UPDATE menus_guardados SET detalle=?, kcal=? WHERE nombre=?',
                        (json.dumps(detalle_n, ensure_ascii=False), kcal, nombre))
            print('  restaurado:', nombre, '-> kcal', kcal)
    print('menus a restaurar desde el respaldo 3-nov: %d%s'
          % (tocados, ' -> APLICADO' if aplicar else ''))
    if aplicar:
        con.commit()
        print('CAMBIOS APLICADOS.')
    else:
        print('DRY-RUN: nada modificado.')
    con.close()

if __name__ == '__main__':
    sys.exit(main())
