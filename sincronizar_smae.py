"""
Sincronizador SMAE: carga en la BD local (y en SMAE-5.xlsx) los alimentos y
platillos exportados del sitio midietasmae.com.mx.

Uso:
    python sincronizar_smae.py catalogo_smae_web.json [platillos_smae_web.json] [--dry-run]

* catalogo_smae_web.json  → lista de alimentos (ObtenerAlimento del sitio).
* platillos_smae_web.json → paquete de platillos (platillos/preparaciones/
  renglonesMenu), tal como lo genera la extracción del sitio.

El script es idempotente: solo inserta lo que no existe (compara por nombre
normalizado). Antes de escribir crea respaldos de la BD y del xlsx, salvo en
--dry-run (solo informa).
"""
import json
import shutil
import sqlite3
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime

RUTA = r'D:\Biblioteca\Nutrición_deportiva'
DB = RUTA + r'\Nutrición_deportiva.db'
XLSX = RUTA + r'\SMAE-5.xlsx'

SUBGRUPOS = [
    "Verduras", "Frutas", "Cereales sin grasa", "Cereales con grasa",
    "Leguminosas", "AOA MBAG", "AOA BAG", "AOA MAG", "AOA AAG",
    "Leche descremada", "Leche semidescremada", "Leche entera",
    "Leche con azúcar", "Aceites y grasas",
    "Aceites y grasas con proteina", "Azucares sin grasa",
    "Azucares con grasa",
]

# Mapeo subgrupo del sitio -> grupo de la BD (calibrado con la intersección)
PAR_ALIMENTO = {
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
    ('Libre', 'Libre'): 'Alimentos libres de energia',
    ('Etanol', 'Etanol'): 'Bebidad alcoholicas',
}

# Para platillos: la app maneja 17 subgrupos sin 'libre' ni alcohol
PAR_PLATILLO = {k: v for k, v in PAR_ALIMENTO.items()
                if v not in ('Alimentos libres de energia',
                             'Bebidad alcoholicas')}

MICROS = ('fibra_g', 'azucar_g', 'vitamina_a_ug', 'vitamina_c_mg',
          'acido_folico_ug', 'hierro_mg', 'calcio_mg', 'potasio_mg',
          'sodio_mg')


def normalizar(s):
    s = unicodedata.normalize('NFKD', str(s or '').strip().lower())
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return ' '.join(s.split())


def a_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def mapear_grupo(g, s, tabla):
    g = ' '.join(str(g or '').strip().split())
    s = ' '.join(str(s or '').strip().split())
    if PAR_ALIMENTO.get((g, s)):
        destino = PAR_ALIMENTO[(g, s)]
    else:
        sn = normalizar(s)
        destino = None
        if g in ('Alimentos de Origen Animal', 'Carne'):
            for prefijo, dest in (('aoaa', 'AOA AAG'), ('aoab', 'AOA BAG'),
                                  ('aoam', 'AOA MAG'), ('aoamb', 'AOA MBAG')):
                if sn.startswith(prefijo):
                    destino = dest
                    break
        elif g == 'Cereal':
            destino = ('Cereales sin grasa' if 'sin grasa' in sn
                       else 'Cereales con grasa' if 'con grasa' in sn else None)
        elif g == 'Azúcares':
            destino = ('Azucares sin grasa' if 'sin grasa' in sn
                       else 'Azucares con grasa' if 'con grasa' in sn else None)
        elif g in ('Grasas', 'grasas'):
            destino = ('Aceites y grasas con proteina' if 'con prote' in sn
                       else 'Aceites y grasas' if 'sin prote' in sn else None)
        elif g == 'Leche':
            destino = ('Leche semidescremada' if 'semidescrem' in sn
                       else 'Leche descremada' if 'descrem' in sn
                       else 'Leche entera' if 'entera' in sn
                       else 'Leche con azúcar' if 'azucar' in sn else None)
    if destino is None:
        return None
    if tabla is PAR_PLATILLO and destino not in SUBGRUPOS:
        return None  # libre/alcohol: la app no tiene ese subgrupo
    return destino


def respaldar(dry):
    if dry:
        return '(omitido por --dry-run)'
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    shutil.copy(DB, RUTA + f'\\Nutrición_deportiva_respaldo_{ts}.db')
    shutil.copy(XLSX, RUTA + f'\\SMAE-5_respaldo_{ts}.xlsx')
    return ts


def sync_alimentos(con, catalogo, dry):
    existentes = {normalizar(r[0]) for r in
                  con.execute('SELECT alimento FROM smae_alimentos')}
    por_grupo = defaultdict(list)
    vistos, omitidos = set(), Counter()
    for c in catalogo:
        clave = normalizar(c.get('Alimento'))
        if not clave or clave in vistos or clave in existentes:
            continue
        vistos.add(clave)
        grupo = mapear_grupo(c.get('Grupo'), c.get('Subgrupo'),
                             PAR_ALIMENTO)
        if grupo is None:
            omitidos[(c.get('Grupo'), c.get('Subgrupo'))] += 1
            continue
        por_grupo[grupo].append({
            'grupo': grupo,
            'alimento': ' '.join(str(c['Alimento']).split()),
            'cantidad_sugerida': a_float(c.get('Cantidad')),
            'unidad': ' '.join(str(c.get('Unidad') or '').split()),
            'peso_bruto_g': 0.0, 'peso_neto_g': 0.0,
            'energia_kcal': a_float(c.get('Energia')),
            'proteina_g': a_float(c.get('Proteina')),
            'lipidos_g': a_float(c.get('Lipidos')),
            'hc_g': a_float(c.get('HidratosCarbono')),
            'fibra_g': 0.0, 'vitamina_a_ug': 0.0, 'vitamina_c_mg': 0.0,
            'acido_folico_ug': 0.0, 'hierro_mg': 0.0, 'potasio_mg': 0.0,
            'calcio_mg': 0.0, 'sodio_mg': 0.0, 'azucar_g': 0.0,
            'indice_glucemico': 0.0, 'carga_glucemica': 0.0,
        })
    total = sum(len(v) for v in por_grupo.values())
    print(f'[alimentos] nuevos: {total} | sin mapeo: {sum(omitidos.values())}')
    if not total:
        return
    if not dry:
        campos = ['grupo', 'alimento', 'cantidad_sugerida', 'unidad',
                  'peso_bruto_g', 'peso_neto_g', 'energia_kcal', 'proteina_g',
                  'lipidos_g', 'hc_g', 'fibra_g', 'vitamina_a_ug',
                  'vitamina_c_mg', 'acido_folico_ug', 'hierro_mg',
                  'potasio_mg', 'calcio_mg', 'sodio_mg', 'azucar_g',
                  'indice_glucemico', 'carga_glucemica']
        with con:
            con.executemany(
                f"INSERT INTO smae_alimentos ({', '.join(campos)}) "
                f"VALUES ({', '.join(':' + c for c in campos)})",
                [f for items in por_grupo.values() for f in items],
            )
    anexar_al_xlsx(por_grupo, dry)


def anexar_al_xlsx(por_grupo, dry):
    import openpyxl
    sys.path.insert(0, RUTA)
    import smae_loader
    if dry:
        for g, items in sorted(por_grupo.items()):
            print(f'[xlsx] {g}: +{len(items)} (dry)')
        return
    wb = openpyxl.load_workbook(XLSX)
    for grupo, items in sorted(por_grupo.items()):
        if grupo not in wb.sheetnames:
            wb.create_sheet(grupo)
            ws = wb[grupo]
            ws.append(['ALIMENTO', 'CANTIDAD SUGERIDA', 'UNIDAD',
                       'PESO REDONDO (G)', 'PESO NETO (G)', 'ENERGÍA (KCAL)',
                       'PROTEINA (G)', 'LIPIDO (G)',
                       'HIDRATO DE CARBONO (G)', 'FIBRA (G)',
                       'ACIDO FOLICO', 'CALCIO (MG)', 'HIERRO (MG)',
                       'SODIO (MG)', 'AZUCAR POR EQUIVALENTE (G)',
                       'INDICE GLUCEMICO', 'CARGA GLUCEMICA'])
        ws = wb[grupo]
        encabezados = None
        for fila in ws.iter_rows(min_row=1, max_row=min(10, ws.max_row),
                                 values_only=True):
            textos = [str(c).strip().lower() if c is not None else ''
                      for c in fila]
            if any('alimento' in t for t in textos):
                encabezados = list(fila)
                break
        if encabezados is None:
            print(f'[xlsx] AVISO: {grupo} sin encabezado detectable; '
                  f'{len(items)} alimentos no anexados')
            continue
        mapa = smae_loader._mapear_columnas(encabezados)
        col_clave = {clave: mapa[clave] for campo, clave in
                     smae_loader.COLUMNAS if clave in mapa}
        ya = {normalizar(r[0]) for r in ws.iter_rows(
            min_row=2, max_col=1, values_only=True) if r[0]}
        for f in items:
            if normalizar(f['alimento']) in ya:
                continue
            fila = [''] * len(encabezados)
            for clave, col in col_clave.items():
                fila[col] = f.get(clave, 0)
            ws.append(fila)
        print(f'[xlsx] {grupo}: +{len(items)}')
    wb.save(XLSX)
    wb.close()


def sync_platillos(con, paquete, dry):
    plat = paquete.get('platillos') or {}
    preps = paquete.get('preparaciones') or {}
    renglones = paquete.get('renglonesMenu') or []
    micros = {}
    for r in con.execute(
        'SELECT alimento, fibra_g, azucar_g, vitamina_a_ug, vitamina_c_mg, '
        'acido_folico_ug, hierro_mg, calcio_mg, potasio_mg, sodio_mg '
        'FROM smae_alimentos'
    ):
        micros[normalizar(r['alimento'])] = r
    existentes = {normalizar(r[0]) for r in
                  con.execute('SELECT nombre FROM platillos')}
    tiempos = defaultdict(Counter)
    for r in renglones:
        if r.get('n'):
            tiempos[normalizar(r['n'])][r.get('t') or ''] += 1

    filas, excluidos = [], Counter()
    for nombre, p in plat.items():
        clave = normalizar(nombre)
        if clave in existentes:
            continue
        ingredientes = []
        tot = {k: 0.0 for k in
               ('energia_kcal', 'proteina_g', 'lipidos_g', 'hc_g') + MICROS}
        for ing in p.get('ing', []):
            sub = mapear_grupo(ing.get('g'), ing.get('s'), PAR_PLATILLO)
            if sub is None:
                excluidos[(ing.get('g'), ing.get('s'))] += 1
                continue
            micro = micros.get(normalizar(ing.get('a')), {})
            reg = {
                'subgrupo_idx': SUBGRUPOS.index(sub),
                'eq_cantidad': a_float(ing.get('eq')),
                'alimento': ing.get('a') or '',
                'cantidad_txt': ' '.join(
                    str(x) for x in [ing.get('q'), ing.get('u')]
                    if x not in (None, '')),
                'conv': '',
                'energia_kcal': a_float(ing.get('e')),
                'proteina_g': a_float(ing.get('p')),
                'lipidos_g': a_float(ing.get('l')),
                'hc_g': a_float(ing.get('h')),
            }
            for k in MICROS:
                reg[k] = a_float(micro[k] if micro else 0)
            ingredientes.append(reg)
            eq = reg['eq_cantidad'] or 1.0
            for k in tot:
                tot[k] += reg[k] * eq
        if not ingredientes:
            continue
        cnt = tiempos.get(clave)
        tiempo = cnt.most_common(1)[0][0] if cnt and len(cnt) else ''
        filas.append({
            'nombre': ' '.join(str(nombre).split()),
            'tiempo_comida': tiempo,
            'ingredientes': json.dumps(ingredientes, ensure_ascii=False),
            'totales': json.dumps(tot, ensure_ascii=False),
            'modo_preparacion': (preps.get(nombre) or '')
            .replace('\n\n', '\n').strip(),
        })
    print(f'[platillos] nuevos: {len(filas)} | ingredientes libre/alcohol '
          f'excluidos: {sum(excluidos.values())}')
    if not filas or dry:
        return
    with con:
        con.executemany(
            "INSERT INTO platillos (nombre, tiempo_comida, ingredientes, "
            "totales, modo_preparacion, creado_en, actualizado_en) "
            "VALUES (:nombre, :tiempo_comida, :ingredientes, :totales, "
            ":modo_preparacion, datetime('now', 'localtime'), "
            "datetime('now', 'localtime'))",
            filas,
        )


def main(argv):
    if '--help' in argv or '-h' in argv or not [a for a in argv
                                                if a != '--dry-run']:
        print(__doc__)
        return 1
    args = [a for a in argv if a != '--dry-run']
    dry = '--dry-run' in argv
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    print('respaldos:', respaldar(dry))
    catalogo = json.load(open(args[0], encoding='utf-8'))
    sync_alimentos(con, catalogo, dry)
    if len(args) > 1:
        paquete = json.load(open(args[1], encoding='utf-8'))
        sync_platillos(con, paquete, dry)
    for tabla, esperado in (('smae_alimentos', None), ('platillos', None)):
        n = con.execute(f'SELECT COUNT(*) FROM {tabla}').fetchone()[0]
        print(f'{tabla}: {n} filas')
    con.close()
    print('LISTO' + (' (dry-run: no se escribió nada)' if dry else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
