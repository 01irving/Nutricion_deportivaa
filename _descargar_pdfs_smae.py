# -*- coding: utf-8 -*-
"""Fase A: descarga los PDF de impresion de todos los menus a D:\\Biblioteca\\menu
y los parsea completos (menus por tiempo, platillos, macros, ingredientes
1/4/6 personas, preparacion, fotos) hacia _extraccion_smae/_datos_smae.json.

Reanudable: si el PDF de un menu ya existe en la carpeta destino y su parseo
quedo registrado, se salta. Los fallos se reintentan una vez.
"""
import json
import re
import sys
import time
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _smae_utils import SesionSMAE, BASE

CARPETA_PDF = Path(r'D:\Biblioteca\menu')
SALIDA = BASE / '_extraccion_smae'
DATOS = SALIDA / '_datos_smae.json'
LOG = SALIDA / '_descarga_log.json'

def normalizar(s):
    s = unicodedata.normalize('NFKD', s or '')
    s = ''.join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r'[^a-z0-9 ]', ' ', s.lower())
    return re.sub(r'\s+', ' ', s).strip()

def num(tok):
    return re.fullmatch(r'\d+(?:[.,]\d+)?', tok or '')

def val(tok):
    return float((tok or '').replace(',', '.'))

# ---------------------------------------------------------------- parser

def clasificar(texto):
    if 'Por menú' in texto:
        return 'menu'
    if 'Por Porción' in texto:
        return 'platillo'
    if 'No. de personas' in texto:
        return 'ingredientes'
    return 'otra'

def parse_menu(pag, doc, datos):
    """Pagina 1: nombre, categoria, totales, y platillos por tiempo."""
    lineas = [l.strip() for l in pag.get_text().splitlines() if l.strip()]
    if not lineas:
        return
    nombre_menu = lineas[0]
    categoria = lineas[1] if len(lineas) > 1 else ''
    registro = datos['menus'].setdefault(nombre_menu, {
        'categoria': categoria, 'totales': {}, 'tiempos': {}})
    # totales por menu
    for i, l in enumerate(lineas):
        if l == 'Por menú':
            sec = lineas[i + 1:i + 14]
            for j, clave in enumerate(('Energía', 'Proteína', 'Lípidos', 'H de C')):
                if clave in sec:
                    k = sec.index(clave)
                    registro['totales'][clave] = val(sec[k + 1])
            break
    # platillos por tiempo; los nombres pueden ocupar 2 renglones, se
    # acumulan en un buffer hasta que aparece la linea de kcal de la fila
    tiempo = None
    buffer_nombre = []
    i = 0
    n = len(lineas)

    def es_fila_kcal(j):
        return (0 < j < n - 3 and num(lineas[j - 1])
                and 'kcal' in lineas[j]
                and lineas[j + 1].endswith('g')
                and lineas[j + 2].endswith('g')
                and lineas[j + 3].endswith('g'))

    while i < n:
        l = lineas[i]
        if l in ('Desayuno', 'Comida', 'Cena', 'Colación', 'Colacion'):
            tiempo = l
            registro['tiempos'].setdefault(tiempo, [])
            buffer_nombre = []
            i += 1
            while i < n and lineas[i] in (
                    'Alimento/Platillo', 'Porción', 'Energía', 'Proteína',
                    'Lípidos', 'H de C'):
                i += 1
            continue
        if tiempo:
            if es_fila_kcal(i):
                fragmentos = list(buffer_nombre)
                # el ultimo fragmento buffered suele ser la porcion
                if fragmentos and fragmentos[-1] == lineas[i - 1]:
                    fragmentos.pop()
                nombre = ' '.join(fragmentos).strip()
                buffer_nombre = []
                registro['tiempos'][tiempo].append({
                    'nombre': nombre,
                    'porcion': val(lineas[i - 1]),
                    'kcal': val(lineas[i].replace(' kcal', '')),
                    'proteina': val(lineas[i + 1].replace(' g', '')),
                    'lipidos': val(lineas[i + 2].replace(' g', '')),
                    'hc': val(lineas[i + 3].replace(' g', '')),
                })
                i += 4
                continue
            if l in ('Alimento/Platillo', 'Porción', 'Energía', 'Proteína',
                     'Lípidos', 'H de C', 'TOTAL', 'EQUIVALENTES'):
                i += 1
                continue
            buffer_nombre.append(l)
        i += 1

def parse_platillo(pag, doc, datos, pendiente_ing):
    lineas = [l for l in pag.get_text().splitlines() if l.strip()]
    limpias = [l.strip() for l in lineas]
    # nombre: puede ocupar 2 renglones; se camina hacia atras desde
    # '1 Porción' hasta topar con el encabezado del menu o la categoria
    idx_porcion = next((i for i, l in enumerate(limpias)
                        if re.match(r'^\d+(\.\d+)?\s*Porci', l)), None)
    if idx_porcion is None or idx_porcion < 2:
        return
    fragmentos = []
    k = idx_porcion - 1
    while k >= 2:
        l = limpias[k]
        if (l == 'Clásico' or l.startswith('Menú ') or num(l)
                or l in ('Desayuno', 'Comida', 'Cena', 'Colación', 'Colacion')):
            break
        fragmentos.insert(0, l)
        k -= 1
    if not fragmentos:
        return
    nombre = ' '.join(fragmentos)
    # tiempo: linea siguiente
    tiempo = limpias[idx_porcion + 1] if idx_porcion + 1 < len(limpias) else ''
    if tiempo not in ('Desayuno', 'Comida', 'Cena', 'Colación', 'Colacion'):
        tiempo = ''
    # etiquetas: lineas con espacios iniciales antes de 'Aportaciones Totales'
    idx_apor = next((i for i, l in enumerate(limpias)
                     if l == 'Aportaciones Totales'), 0)
    etiquetas = [l for l in lineas[:idx_apor]
                 if l.startswith(' ') and l.strip() not in ('', 'Clásico')]
    etiquetas = [l.strip() for l in etiquetas]
    # macros por porcion
    macros = {}
    for clave in ('Energía', 'Proteína', 'Lípidos', 'H de C'):
        if clave in limpias:
            k = limpias.index(clave)
            if k + 1 < len(limpias) and num(limpias[k + 1]):
                macros[clave] = val(limpias[k + 1])
    clave_norm = normalizar(nombre)
    reg = datos['platillos'].setdefault(clave_norm, {
        'nombre': nombre, 'tiempo': tiempo, 'etiquetas': etiquetas,
        'macros': macros, 'menus': set(), 'ingredientes': [], 'preparacion': [],
    })
    reg['menus'] = sorted(set(reg['menus']) | {datos.get('_menu_actual', '')})
    if tiempo and not reg['tiempo']:
        reg['tiempo'] = tiempo
    if macros:
        reg['macros'] = macros or reg['macros']
    for e in etiquetas:
        if e not in reg['etiquetas']:
            reg['etiquetas'].append(e)
    # foto de la pagina
    mejor = None
    for img in pag.get_images(full=True):
        info = doc.extract_image(img[0])
        if info['ext'] in ('jpeg', 'jpg') and 200 <= info['width'] <= 1000 \
                and 80 <= info['height'] <= 500:
            if mejor is None or info['width'] * info['height'] > \
                    mejor['width'] * mejor['height']:
                mejor = info
    if mejor and not reg.get('foto_archivo'):
        archivo = 'foto_%s.%s' % (clave_norm[:80], mejor['ext'])
        (SALIDA / archivo).write_bytes(mejor['image'])
        reg['foto_archivo'] = archivo
    # ingredientes de esta misma pagina?
    if 'No. de personas' in pag.get_text():
        pendiente_ing[0] = clave_norm
        parse_ingredientes(pag.get_text(), reg)
    else:
        pendiente_ing[0] = clave_norm  # vendran en la(s) pagina(s) siguientes

STOP_FILA = ('Ingredientes', 'Preparación', 'Alimento', 'Continuación',
             'Unidad')
PASO = re.compile(r'^\d+\.$')

def parse_ingredientes(texto, reg):
    tokens = texto.split()
    try:
        i = tokens.index('Unidad')
    except ValueError:
        return reg['ingredientes']
    # saltar encabezado '1 4 6'
    i += 1
    while i < len(tokens) and tokens[i] in ('1', '4', '6'):
        i += 1
    filas = []
    while i < len(tokens):
        tok = tokens[i]
        if tok in STOP_FILA or PASO.match(tok):
            break  # fin de la tabla (siguen los pasos o otra seccion)
        if num(tok):  # renglon sin nombre nuevo? no deberia
            i += 1
            continue
        # acumular nombre
        nombre = [tok]
        i += 1
        while i < len(tokens) and not num(tokens[i]) and tokens[i] not in STOP_FILA \
                and not PASO.match(tokens[i]):
            nombre.append(tokens[i])
            i += 1
        cants = []
        while i < len(tokens) and num(tokens[i]) and len(cants) < 3:
            cants.append(val(tokens[i]))
            i += 1
        unidad = ''
        if i < len(tokens) and not num(tokens[i]) and tokens[i] not in STOP_FILA \
                and not PASO.match(tokens[i]):
            unidad = tokens[i]
            i += 1
        filas.append({
            'alimento': ' '.join(nombre),
            'cant1': cants[0] if cants else None,
            'cant4': cants[1] if len(cants) > 1 else None,
            'cant6': cants[2] if len(cants) > 2 else None,
            'unidad': unidad,
        })
    # sustituir/añadir por nombre (una fila por alimento)
    existentes = {f['alimento'] for f in reg['ingredientes']}
    for f in filas:
        if f['alimento'] not in existentes:
            reg['ingredientes'].append(f)
    # preparacion: pasos numerados + lineas de continuacion, sin duplicados
    vistos = set(reg['preparacion'])
    paso_actual = None
    for linea in texto.splitlines():
        l = linea.strip()
        m = re.match(r'^(\d+)\.\s+(.*)$', l)
        if m:
            paso_actual = m.group(2).strip()
            if paso_actual and paso_actual not in vistos:
                reg['preparacion'].append(paso_actual)
                vistos.add(paso_actual)
        elif l and paso_actual is not None and not PASO.match(l.split()[0]
                                                           if l.split() else ''):
            # continuacion del paso en la linea siguiente
            if not re.match(r'^(Alimento|No\. de personas|Unidad|'
                            r'Continuaci|Menú |Clásico)', l):
                reg['preparacion'][-1] += ' ' + l
    return reg['ingredientes']

# ---------------------------------------------------------------- main

def parse_pdf(ruta_pdf, datos, pendiente_ing, nombre_menu):
    import pymupdf
    doc = pymupdf.open(str(ruta_pdf))
    datos['_menu_actual'] = nombre_menu
    for pag in doc:
        texto = pag.get_text()
        tipo = clasificar(texto)
        if tipo == 'menu':
            parse_menu(pag, doc, datos)
        elif tipo == 'platillo':
            parse_platillo(pag, doc, datos, pendiente_ing)
        elif tipo == 'ingredientes':
            clave = pendiente_ing[0]
            if clave and clave in datos['platillos']:
                parse_ingredientes(texto, datos['platillos'][clave])

def main():
    SALIDA.mkdir(exist_ok=True)
    CARPETA_PDF.mkdir(exist_ok=True)
    datos = json.loads(DATOS.read_text(encoding='utf-8')) if DATOS.exists() else {
        'menus': {}, 'platillos': {}}
    log = json.loads(LOG.read_text(encoding='utf-8')) if LOG.exists() else {
        'hechos': [], 'fallidos': []}
    hechos = set(log['hechos'])

    menus = json.load(open(BASE / 'menus_lista_smae_web.json', encoding='utf-8'))
    menus = [m for m in menus
             if (m.get('k') or '0').strip().rstrip('0.').strip() not in ('', '0')]
    pendientes = [m for m in menus if m['i'] not in hechos]
    print('menus con platillos: %d | hechos: %d | pendientes: %d' % (
        len(menus), len(hechos), len(pendientes)), flush=True)

    ses = SesionSMAE()
    t0_run = time.time()
    try:
        for n, m in enumerate(pendientes):
            t0 = time.time()
            nombre_arch = '%s_%s.pdf' % (m['i'], normalizar(m['n'])[:60])
            ruta_pdf = CARPETA_PDF / nombre_arch
            ok = False
            for intento in (1, 2):
                try:
                    pagina = ses.pagina
                    url = ('https://midietasmae.com.mx/Manager/Menu/VisualizaMenu.aspx?id=%s'
                           % m['i'])
                    ses.ir(url, selector_espera='a[href*="Salir"]', timeout_sel=45000)
                    pagina.wait_for_timeout(1200)
                    btn = pagina.get_by_text('Imprimir').first
                    with pagina.expect_download(timeout=30000) as info:
                        btn.click()
                    info.value.save_as(str(ruta_pdf))
                    ok = True
                    break
                except Exception as e:
                    print('  intento %d fallo: %s' % (intento, str(e)[:90]), flush=True)
            if ok:
                try:
                    pend = ['']
                    parse_pdf(ruta_pdf, datos, pend, m['n'])
                    hechos.add(m['i'])
                    log['hechos'] = sorted(hechos)
                except Exception as e:
                    print('  PARSEO fallo: %s' % str(e)[:120], flush=True)
                    log['fallidos'].append(m['i'])
            # guardar estado cada menu
            DATOS.write_text(json.dumps(datos, ensure_ascii=False), encoding='utf-8')
            LOG.write_text(json.dumps(log, ensure_ascii=False), encoding='utf-8')
            restantes = len(pendientes) - n - 1
            ritmo = (time.time() - t0_run) / (n + 1)
            print('%4d/%d %-22s id=%-6s %5.1fs %s | platillos %3d | ETA %.0f min'
                  % (n + 1, len(pendientes), m['n'][:22], m['i'],
                     time.time() - t0, 'OK' if ok else 'FALLO',
                     len(datos['platillos']), ritmo * restantes / 60), flush=True)
    finally:
        ses.cerrar()
        DATOS.write_text(json.dumps(datos, ensure_ascii=False), encoding='utf-8')
        LOG.write_text(json.dumps(log, ensure_ascii=False), encoding='utf-8')
    print('DESCARGA TERMINADA: %d hechos, %d fallidos | platillos: %d | menus: %d'
          % (len(log['hechos']), len(log['fallidos']),
             len(datos['platillos']), len(datos['menus'])), flush=True)

if __name__ == '__main__':
    main()
