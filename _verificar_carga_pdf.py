# -*- coding: utf-8 -*-
"""Verificacion post-carga: compara la BD del proyecto contra el dataset
parseado de los PDF (platillos y menús)."""
import json
import re
import sqlite3
import sys
import unicodedata
from pathlib import Path

BASE = Path(__file__).parent
DATOS = BASE / '_extraccion_smae' / '_datos_smae.json'
BD = BASE / 'Nutrición_deportiva.db'

def normalizar(s):
    s = unicodedata.normalize('NFKD', str(s or ''))
    s = ''.join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r'[^a-z0-9 ]', ' ', s.lower())
    return re.sub(r'\s+', ' ', s).strip()

def num(v):
    try:
        return float(str(v).replace(',', '.'))
    except (TypeError, ValueError):
        return 0.0

def main():
    datos = json.loads(DATOS.read_text(encoding='utf-8'))
    con = sqlite3.connect(BD)
    checks = []

    def ok(cond, msg):
        checks.append(bool(cond))
        print('  %s %s' % ('OK ' if cond else 'FALLO', msg))

    # --- platillos: macros por porcion coinciden con el PDF ---
    cat = {normalizar(n): (i, n) for i, n in
           con.execute('SELECT id_platillo, nombre FROM platillos')}
    revisados = dif_kcal = 0
    for clave, p in datos['platillos'].items():
        match = cat.get(clave)
        if not match:
            continue
        id_p, nombre = match
        row = con.execute('SELECT totales FROM platillos WHERE id_platillo=?',
                          (id_p,)).fetchone()
        tot = json.loads(row[0] or '{}')
        revisados += 1
        if abs(num(tot.get('energia_kcal')) - num(p['macros'].get('Energía'))) > 0.05:
            dif_kcal += 1
            if dif_kcal <= 5:
                print('   kcal difieren: %s bd=%s pdf=%s' % (
                    nombre, tot.get('energia_kcal'), p['macros'].get('Energía')))
    ok(revisados > 0, 'platillos revisados contra PDF: %d' % revisados)
    ok(dif_kcal == 0, 'kcal por porcion identicas al PDF (diferencias: %d)' % dif_kcal)

    # --- platillos con modo de preparacion del PDF ---
    con_prep = 0
    for clave, p in datos['platillos'].items():
        match = cat.get(clave)
        if not match or not p.get('preparacion'):
            continue
        row = con.execute('SELECT modo_preparacion FROM platillos WHERE id_platillo=?',
                          (match[0],)).fetchone()
        esperado = '\n'.join(p['preparacion']).strip()
        if (row[0] or '').strip() == esperado:
            con_prep += 1
    total_prep = sum(1 for p in datos['platillos'].values() if p.get('preparacion')
                     and normalizar(p['nombre']) in cat)
    ok(con_prep == total_prep,
       'modo de preparacion = PDF en %d de %d platillos' % (con_prep, total_prep))

    # --- imagenes: los platillos con foto del sitio la tienen en la BD ---
    con_foto = 0
    con_foto_ok = 0
    for clave, p in datos['platillos'].items():
        match = cat.get(clave)
        if not match or not p.get('foto_archivo'):
            continue
        con_foto += 1
        row = con.execute('SELECT imagen_nombre FROM platillos WHERE id_platillo=?',
                          (match[0],)).fetchone()
        if row and 'SMAE Premium' in (row[0] or ''):
            con_foto_ok += 1
    ok(con_foto == con_foto_ok,
       'imagenes acreditadas al sitio: %d de %d' % (con_foto_ok, con_foto))

    # --- menus: estructura por tiempo = PDF ---
    menus_bd = {n: d for n, d in con.execute(
        'SELECT nombre, detalle FROM menus_guardados')}
    revisados_m = iguales_m = 0
    for nombre_menu, m in datos['menus'].items():
        if nombre_menu not in menus_bd:
            continue
        d = json.loads(menus_bd[nombre_menu])
        esperados = []
        for t in ('Desayuno', 'Colación', 'Comida', 'Cena'):
            lista = m['tiempos'].get(t) or []
            if lista:
                esperados.append((t, [r['nombre'] for r in lista]))
        obtenidos = []
        lunes = d['dias'].get('Lunes', {})
        for t in d.get('tiempos', []):
            pass
        for slot_txt in sorted(lunes.get('platillos', {}),
                               key=lambda s: int(s) if s.isdigit() else 9):
            idx = d.get('tiempos', []).index  # orden por tiempos listado
        # reconstruir por tiempos declarados
        obtenidos = []
        for pos, t in enumerate(d.get('tiempos', [])):
            txt = lunes.get('platillos', {}).get(str(pos), '')
            if txt:
                obtenidos.append((t, [x.strip() for x in txt.split(' + ')]))
        revisados_m += 1
        if esperados == obtenidos:
            iguales_m += 1
        elif iguales_m + (revisados_m - iguales_m) <= 3 and esperados != obtenidos:
            print('   menu difiere: %s' % nombre_menu)
            print('     pdf : %s' % (esperados,))
            print('     bd  : %s' % (obtenidos,))
    ok(revisados_m > 0, 'menus revisados: %d' % revisados_m)
    ok(iguales_m == revisados_m,
       'estructura de menús (tiempos+platillos) identica al PDF en %d de %d'
       % (iguales_m, revisados_m))

    con.close()
    print()
    print('VERIFICACION TODO OK' if all(checks) else
          'HUBO FALLOS: %d/%d' % (checks.count(False), len(checks)))
    return 0 if all(checks) else 1

if __name__ == '__main__':
    sys.exit(main())
