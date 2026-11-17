# -*- coding: utf-8 -*-
"""Fase B: escribe en la BD del proyecto la informacion extraida de los PDF
de midietasmae (Fase A: _extraccion_smae/_datos_smae.json).

Regla del autor: "si algo no coincide, se borra y se escribe de nuevo":
  * ingredientes: la lista del PDF es la verdad; se reescribe completa
    (los renglones existentes aportan subgrupo/micronutrientes; las
    cantidades se actualizan al 1-persona del PDF; sobrantes se borran;
    faltantes se agregan desde platillos_smae_web.json o como renglon
    minimo).
  * totales: macros por porcion desde el PDF; fibra/micros/equivalentes
    recalculados sumando los renglones finales.
  * modo_preparacion: pasos numerados del PDF.
  * imagen: foto del PDF si hay.
  * menus_guardados: se reescribe el detalle (platillos por tiempo y
    renglones portadores) desde la pagina 1 del PDF, con sus kcal.
Todo con respaldo previo de la BD y bitacora de cambios.
"""
import json
import re
import shutil
import sqlite3
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).parent
DATOS = BASE / '_extraccion_smae' / '_datos_smae.json'
FOTOS_EXTRA = BASE / '_extraccion_smae'
FOTOS_ANTIGUAS = BASE / '_fotos_smae' / '_mapeo.json'
PLAT_JSON = BASE / 'platillos_smae_web.json'
AUDIT = BASE / '_extraccion_smae' / '_cambios_bd.json'
# BD destino: proyecto por defecto; la instalada con --bd dist
BD = BASE / 'Nutrición_deportiva.db'
BD_DIST = BASE / 'dist' / 'NutricionDeportiva' / 'Nutrición_deportiva.db'

SUBGRUPOS = [
    "Verduras", "Frutas", "Cereales sin grasa", "Cereales con grasa",
    "Leguminosas", "AOA MBAG", "AOA BAG", "AOA MAG", "AOA AAG",
    "Leche descremada", "Leche semidescremada", "Leche entera",
    "Leche con azúcar", "Aceites y grasas",
    "Aceites y grasas con proteina", "Azucares sin grasa",
    "Azucares con grasa",
]
PAR_PLATILLO = {
    ('Verduras', 'Verduras'): 'Verduras',
    ('Frutas', 'Frutas'): 'Frutas',
    ('Cereal', 'Sin grasa'): 'Cereales sin grasa',
    ('Cereal', 'Con grasa'): 'Cereales con grasa',
    ('Leguminosas', 'Leguminosas'): 'Leguminosas',
    ('Alimentos de Origen Animal', 'AOAA'): 'AOA AAG',
    ('Alimentos de Origen Animal', 'AOAB'): 'AOA BAG',
    ('Alimentos de Origen Animal', 'AOAM'): 'AOA MAG',
    ('Alimentos de Origen Animal', 'AOAMB'): 'AOA MBAG',
    ('Carne', 'AOAA'): 'AOA AAG',
    ('Carne', 'AOAB'): 'AOA BAG',
    ('Carne', 'AOAM'): 'AOA MAG',
    ('Carne', 'AOAMB'): 'AOA MBAG',
    ('Leche', 'Descremada'): 'Leche descremada',
    ('Leche', 'Semidescremada'): 'Leche semidescremada',
    ('Leche', 'Entera'): 'Leche entera',
    ('Leche', 'Con azúcar'): 'Leche con azúcar',
    ('Grasas', 'Sin proteína'): 'Aceites y grasas',
    ('Grasas', 'Con proteína'): 'Aceites y grasas con proteina',
    ('Azúcares', 'Sin grasa'): 'Azucares sin grasa',
    ('Azúcares', 'Con grasa'): 'Azucares con grasa',
}
MICROS = ('fibra_g', 'azucar_g', 'vitamina_a_ug', 'vitamina_c_mg',
          'acido_folico_ug', 'hierro_mg', 'calcio_mg', 'potasio_mg',
          'sodio_mg')
CLAVES_MICRO = ('energia_kcal', 'proteina_g', 'lipidos_g', 'hc_g') + MICROS
CREDITO = 'Foto: SMAE Premium (midietasmae.com.mx)'
TIEMPOS_ORDEN = ('Desayuno', 'Colación', 'Comida', 'Cena')

def normalizar(s):
    s = unicodedata.normalize('NFKD', str(s or ''))
    s = ''.join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r'[^a-z0-9 ]', ' ', s.lower())
    return re.sub(r'\s+', ' ', s).strip()

def num(v, defa=0.0):
    try:
        return float(str(v).replace(',', '.'))
    except (TypeError, ValueError):
        return defa

def fila_vacia(nombre, cantidad_txt='', unidad=''):
    fila = {k: 0.0 for k in CLAVES_MICRO}
    fila.update({'subgrupo_idx': None, 'eq_cantidad': 1.0,
                 'alimento': nombre, 'cantidad_txt': cantidad_txt,
                 'conv': '', 'grupo': '', 'unidad': unidad})
    return fila

def fila_desde_json(ing):
    """Renglon en formato de la app desde un ing de platillos_smae_web.json."""
    nombre_grupo = PAR_PLATILLO.get((ing.get('g', ''), ing.get('s', '')))
    try:
        idx = SUBGRUPOS.index(nombre_grupo) if nombre_grupo else None
    except ValueError:
        idx = None
    fila = {k: 0.0 for k in CLAVES_MICRO}
    fila.update({
        'subgrupo_idx': idx,
        'eq_cantidad': num(ing.get('eq'), 1.0),
        'alimento': ing.get('a', ''),
        'cantidad_txt': f"{ing.get('q', '')} {ing.get('u', '')}".strip(),
        'conv': '',
        'grupo': ing.get('g', ''),
        'unidad': ing.get('u', ''),
        'energia_kcal': num(ing.get('e')),
        'proteina_g': num(ing.get('p')),
        'lipidos_g': num(ing.get('l')),
        'hc_g': num(ing.get('h')),
    })
    return fila

def totales_desde(macros, filas):
    tot = {k: 0.0 for k in CLAVES_MICRO}
    equivalentes = {}
    for f in filas:
        eq = num(f.get('eq_cantidad'), 1.0)
        for k in CLAVES_MICRO:
            tot[k] += num(f.get(k)) * eq
        idx = f.get('subgrupo_idx')
        if isinstance(idx, int) and 0 <= idx < len(SUBGRUPOS):
            equivalentes[SUBGRUPOS[idx]] = round(
                equivalentes.get(SUBGRUPOS[idx], 0.0) + eq, 3)
    # macros por porcion manda el PDF
    if macros:
        tot['energia_kcal'] = num(macros.get('Energía'), tot['energia_kcal'])
        tot['proteina_g'] = num(macros.get('Proteína'), tot['proteina_g'])
        tot['lipidos_g'] = num(macros.get('Lípidos'), tot['lipidos_g'])
        tot['hc_g'] = num(macros.get('H de C'), tot['hc_g'])
    for k in tot:
        tot[k] = round(tot[k], 4)
    tot['equivalentes'] = dict(sorted(equivalentes.items(),
                                      key=lambda x: -x[1]))
    return tot

def main():
    aplicar = '--aplicar' in sys.argv
    global BD
    if '--bd' in sys.argv:
        BD = Path(sys.argv[sys.argv.index('--bd') + 1])
    elif '--dist' in sys.argv:
        BD = BD_DIST
    datos = json.loads(DATOS.read_text(encoding='utf-8'))
    plat_pdf = datos['platillos']
    menus_pdf = datos['menus']

    try:
        plat_json = json.loads(PLAT_JSON.read_text(encoding='utf-8'))['platillos']
    except Exception:
        plat_json = {}
    json_por_platillo = {normalizar(k): v.get('ing', [])
                         for k, v in plat_json.items()}

    try:
        mapeo_fotos = json.loads(FOTOS_ANTIGUAS.read_text(encoding='utf-8'))
    except Exception:
        mapeo_fotos = {}

    con = sqlite3.connect(BD)
    catalogo = {normalizar(n): (i, n) for i, n in
                con.execute('SELECT id_platillo, nombre FROM platillos')}

    audit = {'platillos': {}, 'menus': {}, 'nuevos': [], 'sin_match': []}
    actualizaciones = []
    inserciones = []

    for clave, p in plat_pdf.items():
        match = catalogo.get(clave)
        if not match:
            # platillo del sitio que no existe en el catalogo: se inserta
            # completo (ingredientes SMAE de platillos_smae_web.json si hay)
            filas_ins = []
            for f in p['ingredientes']:
                norm_a = normalizar(f['alimento'])
                base = None
                for ing in json_por_platillo.get(clave, []):
                    if normalizar(ing.get('a', '')) == norm_a:
                        base = fila_desde_json(ing)
                        break
                if base is None:
                    base = fila_vacia(f['alimento'])
                else:
                    base['alimento'] = f['alimento']
                if f.get('cant1') is not None:
                    base['cantidad_txt'] = (
                        f"{f['cant1']:g} {f.get('unidad', '')}".strip())
                    base['unidad'] = f.get('unidad', '') or base.get('unidad', '')
                filas_ins.append(base)
            tot_ins = totales_desde(p.get('macros'), filas_ins)
            blob_ins = None
            foto = p.get('foto_archivo')
            if foto and (FOTOS_EXTRA / foto).exists():
                blob_ins = (FOTOS_EXTRA / foto).read_bytes()
            elif clave in mapeo_fotos:
                f2 = FOTOS_ANTIGUAS.parent / mapeo_fotos[clave]['archivo']
                if f2.exists():
                    blob_ins = f2.read_bytes()
            inserciones.append({
                'nombre': p['nombre'], 'tiempo': p.get('tiempo') or 'Comida',
                'ingredientes': filas_ins, 'totales': tot_ins,
                'modo': '\n'.join(p.get('preparacion') or []),
                'blob': blob_ins,
            })
            audit['nuevos'].append(p['nombre'])
            continue
        id_p, nombre = match
        row = con.execute(
            'SELECT ingredientes, totales, modo_preparacion, imagen_blob '
            'FROM platillos WHERE id_platillo=?', (id_p,)).fetchone()
        try:
            filas_db = json.loads(row[0] or '[]')
        except (json.JSONDecodeError, TypeError):
            filas_db = []
        try:
            totales_db = json.loads(row[1] or '{}')
        except (json.JSONDecodeError, TypeError):
            totales_db = {}

        # --- ingredientes: PDF manda ---
        ing_json = json_por_platillo.get(clave, [])
        json_libres = {normalizar(i.get('a', '')): i for i in ing_json}
        usados_db = set()
        filas_nuevas = []
        altas, cant_cambiadas = [], []
        for f in p['ingredientes']:
            norm = normalizar(f['alimento'])
            base = None
            for i, r in enumerate(filas_db):
                if i in usados_db:
                    continue
                if normalizar(r.get('alimento')) == norm:
                    base = dict(r)
                    usados_db.add(i)
                    break
            if base is None and norm in json_libres:
                base = fila_desde_json(json_libres[norm])
            if base is None:
                base = fila_vacia(f['alimento'])
            else:
                base['alimento'] = f['alimento']
            if f.get('cant1') is not None:
                cant_txt = f"{f['cant1']:g} {f.get('unidad', '')}".strip()
                viejo = (base.get('cantidad_txt') or '').strip()
                if viejo != cant_txt:
                    cant_cambiadas.append('%s: %s -> %s' % (
                        f['alimento'], viejo or '(vacío)', cant_txt))
                base['cantidad_txt'] = cant_txt
                base['unidad'] = f.get('unidad', '') or base.get('unidad', '')
            filas_nuevas.append(base)
        bajas = [r['alimento'] for i, r in enumerate(filas_db)
                 if i not in usados_db]
        # --- totales ---
        tot_nuevo = totales_desde(p.get('macros'), filas_nuevas)
        # --- modo de preparacion ---
        modo_nuevo = '\n'.join(p.get('preparacion') or [])
        # --- imagen ---
        blob = None
        foto = p.get('foto_archivo')
        if foto and (FOTOS_EXTRA / foto).exists():
            blob = (FOTOS_EXTRA / foto).read_bytes()
        elif clave in mapeo_fotos:
            f2 = FOTOS_ANTIGUAS.parent / mapeo_fotos[clave]['archivo']
            if f2.exists():
                blob = f2.read_bytes()

        cambios = {}
        if bajas:
            cambios['ingredientes_borrados'] = bajas
        if altas:
            cambios['ingredientes_agregados'] = altas
        if cant_cambiadas:
            cambios['cantidades'] = cant_cambiadas
        dif_tot = {k: (totales_db.get(k), tot_nuevo[k])
                   for k in CLAVES_MICRO
                   if abs(num(totales_db.get(k)) - tot_nuevo[k]) > 0.01}
        if dif_tot:
            cambios['totales'] = {k: [v[0], v[1]] for k, v in dif_tot.items()}
        modo_viejo = (row[2] or '').strip()
        if modo_nuevo and modo_viejo != modo_nuevo:
            cambios['modo_preparacion'] = True
        audit['platillos'][nombre] = cambios

        actualizaciones.append({
            'id': id_p, 'nombre': nombre, 'ingredientes': filas_nuevas,
            'totales': tot_nuevo, 'modo': modo_nuevo, 'blob': blob,
        })

    # --- menus ---
    menus_bd = {n: i for i, n in con.execute(
        'SELECT id_menu_guardado, nombre FROM menus_guardados')}
    for nombre_menu, m in menus_pdf.items():
        if nombre_menu not in menus_bd:
            continue
        detalle = {'tiempos': [], 'dias': {}}
        lunes = {'platillos': {}, 'alimentos': {}}
        slot = 0
        total_kcal = 0.0
        for tiempo in TIEMPOS_ORDEN:
            lista = m['tiempos'].get(tiempo) or []
            if not lista:
                continue
            detalle['tiempos'].append(tiempo)
            nombres = []
            filas = []
            for r in lista:
                nombres.append(r['nombre'])
                fila = fila_vacia(r['nombre'], unidad='Porción')
                fila['eq_cantidad'] = num(r.get('porcion'), 1.0)
                fila['energia_kcal'] = num(r.get('kcal'))
                fila['proteina_g'] = num(r.get('proteina'))
                fila['lipidos_g'] = num(r.get('lipidos'))
                fila['hc_g'] = num(r.get('hc'))
                filas.append(fila)
                total_kcal += fila['energia_kcal'] * fila['eq_cantidad']
            lunes['platillos'][str(slot)] = ' + '.join(nombres)
            lunes['alimentos'][str(slot)] = filas
            slot += 1
        detalle['dias']['Lunes'] = lunes
        audit['menus'][nombre_menu] = {
            'tiempos': detalle['tiempos'],
            'platillos_por_tiempo': {
                t: [x['nombre'] for x in m['tiempos'].get(t) or []]
                for t in detalle['tiempos']},
        }
        actualizaciones.append({
            'menu_id': menus_bd[nombre_menu], 'nombre_menu': nombre_menu,
            'detalle': detalle, 'kcal': int(round(total_kcal)),
        })

    print('platillos del PDF con match en catalogo : %d' % (
        len(audit['platillos'])))
    print('platillos nuevos a insertar             : %d (%s)' % (
        len(inserciones), ', '.join(a['nombre'] for a in inserciones)))
    print('menus a reescribir                      : %d' % len(audit['menus']))
    con_cambios_ing = sum(1 for c in audit['platillos'].values()
                          if c.get('ingredientes_borrados') or
                          c.get('cantidades'))
    con_cambios_modo = sum(1 for c in audit['platillos'].values()
                           if c.get('modo_preparacion'))
    print('platillos con ingredientes/cantidades distintas: %d' % con_cambios_ing)
    print('platillos con preparacion distinta      : %d' % con_cambios_modo)

    if not aplicar:
        print('DRY-RUN: nada modificado. Usa --aplicar.')
        con.close()
        return 0

    # respaldo
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    respaldo = BD.with_name('%s_respaldo_datos_pdf_%s.db' % (BD.stem, stamp))
    shutil.copy(BD, respaldo)
    print('respaldo:', respaldo.name)

    ahora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    for ins in inserciones:
        con.execute(
            'INSERT INTO platillos (nombre, tiempo_comida, ingredientes, '
            'totales, modo_preparacion, imagen_blob, imagen_nombre, '
            'creado_en, actualizado_en) VALUES (?,?,?,?,?,?,?,?,?)',
            (ins['nombre'], ins['tiempo'],
             json.dumps(ins['ingredientes'], ensure_ascii=False),
             json.dumps(ins['totales'], ensure_ascii=False),
             ins['modo'], ins['blob'],
             CREDITO if ins['blob'] else None, ahora, ahora))
    for a in actualizaciones:
        if 'id' in a:
            con.execute(
                'UPDATE platillos SET ingredientes=?, totales=?, '
                'modo_preparacion=?, actualizado_en=? '
                + (', imagen_blob=?, imagen_nombre=?' if a['blob'] else '')
                + ' WHERE id_platillo=?',
                (json.dumps(a['ingredientes'], ensure_ascii=False),
                 json.dumps(a['totales'], ensure_ascii=False),
                 a['modo'], ahora)
                + ((a['blob'], CREDITO) if a['blob'] else ())
                + (a['id'],))
        else:
            con.execute(
                'UPDATE menus_guardados SET detalle=?, kcal=? WHERE '
                'id_menu_guardado=?',
                (json.dumps(a['detalle'], ensure_ascii=False),
                 a['kcal'], a['menu_id']))
    con.commit()
    AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=1),
                     encoding='utf-8')
    print('APLICADO: %d escrituras. Bitacora en %s' % (
        len(actualizaciones), AUDIT.name))
    con.close()
    return 0

if __name__ == '__main__':
    sys.exit(main())
