# -*- coding: utf-8 -*-
"""Actualiza SOLO modo_preparacion de los platillos en una BD destino con las
preparaciones parseadas de los PDF (_extraccion_smae/_datos_smae.json).
Uso: python _limpiar_modos_pdf.py <bd_destino> [--aplicar]
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

def normalizar(s):
    s = unicodedata.normalize('NFKD', str(s or ''))
    s = ''.join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r'[^a-z0-9 ]', ' ', s.lower())
    return re.sub(r'\s+', ' ', s).strip()

def main():
    destino = Path(sys.argv[1])
    aplicar = '--aplicar' in sys.argv
    datos = json.loads(DATOS.read_text(encoding='utf-8'))
    con = sqlite3.connect(destino)
    cat = {normalizar(n): (i, n) for i, n in
           con.execute('SELECT id_platillo, nombre FROM platillos')}
    cambios = []
    for clave, p in datos['platillos'].items():
        match = cat.get(clave)
        if not match or not p.get('preparacion'):
            continue
        modo = '\n'.join(p['preparacion'])
        id_p, nombre = match
        row = con.execute('SELECT modo_preparacion FROM platillos WHERE '
                          'id_platillo=?', (id_p,)).fetchone()
        viejo = (row[0] or '').strip()
        if viejo != modo:
            cambios.append((id_p, nombre, viejo, modo))
    print('BD: %s | platillos con modo a corregir: %d' % (
        destino.name, len(cambios)))
    for _, nombre, viejo, _ in cambios[:8]:
        print('   %s | antes: %s' % (nombre[:34], (viejo or '(vacío)')[:60].replace('\n', ' / ')))
    if not aplicar:
        print('DRY-RUN: nada modificado. Usa --aplicar.')
        con.close()
        return 0
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    respaldo = destino.with_name('%s_respaldo_modos_%s.db' % (
        destino.stem, stamp))
    shutil.copy(destino, respaldo)
    print('respaldo:', respaldo.name)
    ahora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    for id_p, _, _, modo in cambios:
        con.execute('UPDATE platillos SET modo_preparacion=?, actualizado_en=? '
                    'WHERE id_platillo=?', (modo, ahora, id_p))
    con.commit()
    print('APLICADO: %d modos corregidos' % len(cambios))
    con.close()
    return 0

if __name__ == '__main__':
    sys.exit(main())
