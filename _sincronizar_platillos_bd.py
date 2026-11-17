# -*- coding: utf-8 -*-
"""Alinea la tabla platillos de una BD destino con la del proyecto, POR
NOMBRE (los ids pueden diferir entre BDs): actualiza tiempo, ingredientes,
totales, modo de preparacion e imagen de los que existen, e inserta los
faltantes. No toca pacientes ni menus.
Uso: python _sincronizar_platillos_bd.py <bd_destino> [--aplicar]
"""
import re
import shutil
import sqlite3
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).parent
PROYECTO = BASE / 'Nutrición_deportiva.db'

def normalizar(s):
    s = unicodedata.normalize('NFKD', str(s or ''))
    s = ''.join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r'[^a-z0-9 ]', ' ', s.lower())
    return re.sub(r'\s+', ' ', s).strip()

def main():
    destino = Path(sys.argv[1])
    aplicar = '--aplicar' in sys.argv
    con_p = sqlite3.connect(PROYECTO)
    con_p.row_factory = sqlite3.Row
    proyecto = {r['nombre']: r for r in
                con_p.execute('SELECT * FROM platillos')}
    con_d = sqlite3.connect(destino)
    con_d.row_factory = sqlite3.Row
    actuales = {r['nombre']: r for r in
                con_d.execute('SELECT * FROM platillos')}
    print('destino: %s | proyecto: %d platillos | destino: %d' % (
        destino.name, len(proyecto), len(actuales)))

    actualizaciones = []
    inserciones = []
    imagenes_distintas = 0
    for clave, fila_p in proyecto.items():
        if clave not in actuales:
            inserciones.append(fila_p)
            continue
        fila_d = actuales[clave]
        if (fila_p['imagen_blob'] or b'') != (fila_d['imagen_blob'] or b''):
            imagenes_distintas += 1
        if any((fila_p[c] or '') != (fila_d[c] or '') for c in (
                'tiempo_comida', 'ingredientes', 'totales', 'modo_preparacion',
                'imagen_blob', 'imagen_nombre')):
            actualizaciones.append(fila_p)
    print('platillos a actualizar (datos/imagen distintos): %d' % len(actualizaciones))
    print('   de ellos con imagen distinta: %d' % imagenes_distintas)
    print('platillos faltantes a insertar            : %d' % len(inserciones))

    if not aplicar:
        print('DRY-RUN: nada modificado. Usa --aplicar.')
        con_p.close()
        con_d.close()
        return 0

    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    respaldo = destino.with_name('%s_respaldo_sincronia_platillos_%s.db' % (
        destino.stem, stamp))
    shutil.copy(destino, respaldo)
    print('respaldo:', respaldo.name)

    ahora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    campos = ('tiempo_comida', 'ingredientes', 'totales', 'modo_preparacion',
              'imagen_blob', 'imagen_nombre', 'actualizado_en')
    for f in actualizaciones:
        con_d.execute(
            'UPDATE platillos SET tiempo_comida=?, ingredientes=?, totales=?, '
            'modo_preparacion=?, imagen_blob=?, imagen_nombre=?, '
            'actualizado_en=? WHERE id_platillo=?',
            (f['tiempo_comida'], f['ingredientes'], f['totales'],
             f['modo_preparacion'], f['imagen_blob'], f['imagen_nombre'],
             ahora, f['id_platillo']))
    for f in inserciones:
        con_d.execute(
            'INSERT INTO platillos (nombre, tiempo_comida, ingredientes, '
            'totales, imagen_nombre, imagen_blob, modo_preparacion, '
            'creado_en, actualizado_en) VALUES (?,?,?,?,?,?,?,?,?)',
            (f['nombre'], f['tiempo_comida'], f['ingredientes'], f['totales'],
             f['imagen_nombre'], f['imagen_blob'], f['modo_preparacion'],
             ahora, ahora))
    con_d.commit()
    print('APLICADO: %d actualizaciones + %d inserciones' % (
        len(actualizaciones), len(inserciones)))
    con_p.close()
    con_d.close()
    return 0

if __name__ == '__main__':
    sys.exit(main())
