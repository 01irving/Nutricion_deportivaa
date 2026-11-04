"""
Inserta los menús de Mi Dieta SMAE (precargados + propios del sitio) en la
tabla menus_guardados de la app, a partir de:
  * menus_lista_smae_web.json  → [{i: IdMenu, n: nombre, k: energia, t: esPlantilla}]
  * platillos_smae_web.json    → paquete con 'renglonesMenu' (m, t, n, p, u, e, pr, l, h)

Los precargados son menús de un día: se guardan en 'Lunes' con un registro
portador de macros por platillo (subgrupo_idx None → no altera distribuciones).
"""
import json
import shutil
import sqlite3
import unicodedata
from collections import defaultdict
from datetime import datetime

RUTA = r'D:\Biblioteca\Nutrición_deportiva'
DB = RUTA + r'\Nutrición_deportiva.db'
TIEMPOS = ['Desayuno', 'Colación', 'Comida', 'Cena']


def normalizar(s):
    s = unicodedata.normalize('NFKD', str(s or '').strip().lower())
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return ' '.join(s.split())


def a_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


lista = json.load(open('menus_lista_smae_web.json', encoding='utf-8'))
paquete = json.load(open('platillos_smae_web.json', encoding='utf-8'))
por_menu = defaultdict(lambda: defaultdict(list))
for r in paquete.get('renglonesMenu', []):
    if r.get('err') or not r.get('n'):
        continue
    por_menu[r['m']][r['t']].append(r)

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row
existentes = {normalizar(r['nombre']) for r in con.execute(
    'SELECT nombre FROM menus_guardados')}

ts = datetime.now().strftime('%Y%m%d_%H%M%S')
shutil.copy(DB, RUTA + f'\\Nutrición_deportiva_respaldo_{ts}.db')
print('respaldo DB:', ts)

insertados = 0
usados = set(existentes)
for m in lista:
    nombre = ' '.join(str(m.get('n') or '').split())
    if not nombre:
        continue
    clave = normalizar(nombre)
    if clave in usados:
        continue
    usados.add(clave)
    filas = por_menu.get(m['i'])
    if not filas:
        continue
    platillos, alimentos = {}, {}
    for idx, tiempo in enumerate(TIEMPOS):
        grupo = filas.get(tiempo)
        if not grupo:
            continue
        registros = []
        nombres = []
        for r in grupo:
            cs = a_float(r.get('p'))
            registros.append({
                'subgrupo_idx': None,
                'eq_cantidad': 1,
                'alimento': r['n'],
                'grupo': '',
                'cantidad_sugerida': cs,
                'unidad': (r.get('u') or '').strip(),
                'energia_kcal': a_float(r.get('e')) or 0.0,
                'proteina_g': a_float(r.get('pr')) or 0.0,
                'lipidos_g': a_float(r.get('l')) or 0.0,
                'hc_g': a_float(r.get('h')) or 0.0,
                'fibra_g': 0.0, 'azucar_g': 0.0, 'vitamina_a_ug': 0.0,
                'vitamina_c_mg': 0.0, 'acido_folico_ug': 0.0, 'hierro_mg': 0.0,
                'calcio_mg': 0.0, 'potasio_mg': 0.0, 'sodio_mg': 0.0,
            })
            nombres.append(r['n'])
        platillos[str(idx)] = ' + '.join(nombres)
        alimentos[str(idx)] = registros
    if not platillos:
        continue
    detalle = {'tiempos': TIEMPOS,
               'dias': {d: {'platillos': {}, 'alimentos': {}}
                        for d in ['Lunes', 'Martes', 'Miércoles', 'Jueves',
                                  'Viernes', 'Sábado', 'Domingo']}}
    detalle['dias']['Lunes'] = {'platillos': platillos,
                                'alimentos': alimentos}
    with con:
        con.execute(
            "INSERT INTO menus_guardados (nombre, kcal, detalle, creado_en) "
            "VALUES (?, ?, ?, datetime('now', 'localtime'))",
            (nombre, round(a_float(m.get('k')) or 0),
             json.dumps(detalle, ensure_ascii=False)),
        )
    insertados += 1

total = con.execute('SELECT COUNT(*) FROM menus_guardados').fetchone()[0]
print(f'menus insertados: {insertados} | total en BD: {total}')
con.close()
print('LISTO')
