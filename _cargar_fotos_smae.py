# -*- coding: utf-8 -*-
"""Carga al catalogo las fotos extraidas de midietasmae (_fotos_smae/_mapeo.json).

* Respalda ambas BD antes de tocar.
* Empareja por nombre normalizado (sin acentos ni signos).
* UPDATE platillos SET imagen_blob, imagen_nombre, actualizado_en por id.
* Aplica lo mismo a la BD instalada (dist) usando los mismos ids.
* Informa emparejados / sin foto / sin contraparte.
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
FOTOS = BASE / '_fotos_smae'
MAPEO = FOTOS / '_mapeo.json'
BD_PROYECTO = BASE / 'Nutrición_deportiva.db'
BD_DIST = BASE / 'dist' / 'NutricionDeportiva' / 'Nutrición_deportiva.db'
CREDITO = 'Foto: SMAE Premium (midietasmae.com.mx)'

def normalizar(s):
    s = unicodedata.normalize('NFKD', s or '')
    s = ''.join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r'[^a-z0-9 ]', ' ', s.lower())
    return re.sub(r'\s+', ' ', s).strip()

def respaldar(ruta):
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    destino = ruta.with_name('%s_respaldo_fotos_smae_%s.db' % (ruta.stem, stamp))
    shutil.copy(ruta, destino)
    return destino

def main():
    aplicar = '--aplicar' in sys.argv
    mapeo = json.loads(MAPEO.read_text(encoding='utf-8'))
    print('fotos en el mapa: %d' % len(mapeo))

    con = sqlite3.connect(BD_PROYECTO)
    platillos = con.execute(
        'SELECT id_platillo, nombre FROM platillos ORDER BY id_platillo').fetchall()
    actualizaciones = []
    sin_foto = []
    for id_p, nombre in platillos:
        clave = normalizar(nombre)
        reg = mapeo.get(clave)
        if not reg:
            sin_foto.append(nombre)
            continue
        blob = (FOTOS / reg['archivo']).read_bytes()
        actualizaciones.append((id_p, nombre, blob))
    print('platillos del catalogo      : %d' % len(platillos))
    print('con foto del sitio          : %d' % len(actualizaciones))
    print('sin foto en el sitio        : %d' % len(sin_foto))
    for n in sin_foto[:20]:
        print('    sin foto:', n)
    if len(sin_foto) > 20:
        print('    ... y %d mas' % (len(sin_foto) - 20))

    if not aplicar:
        print('DRY-RUN: nada modificado. Usa --aplicar.')
        con.close()
        return 0

    r1 = respaldar(BD_PROYECTO)
    print('respaldo proyecto :', r1.name)
    ahora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    con.executemany(
        'UPDATE platillos SET imagen_blob=?, imagen_nombre=?, actualizado_en=? '
        'WHERE id_platillo=?',
        [(blob, CREDITO, ahora, id_p) for id_p, _, blob in actualizaciones])
    con.commit()

    # misma carga por id en la instalada (mismos ids, verificado antes)
    con2 = sqlite3.connect(BD_DIST)
    ids_dist = {r[0] for r in con2.execute('SELECT id_platillo FROM platillos')}
    faltan_dist = {id_p for id_p, _, _ in actualizaciones} - ids_dist
    if faltan_dist:
        print('ADVERTENCIA: %d ids no existen en dist; se omiten' % len(faltan_dist))
    r2 = respaldar(BD_DIST)
    print('respaldo dist     :', r2.name)
    con2.executemany(
        'UPDATE platillos SET imagen_blob=?, imagen_nombre=?, actualizado_en=? '
        'WHERE id_platillo=?',
        [(blob, CREDITO, ahora, id_p) for id_p, _, blob in actualizaciones
         if id_p in ids_dist])
    con2.commit()
    con.close()
    con2.close()
    print('ACTUALIZADOS: %d platillos en ambas BD' % len(actualizaciones))
    return 0

if __name__ == '__main__':
    sys.exit(main())
